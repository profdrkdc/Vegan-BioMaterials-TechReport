# src/run_pipeline.py

import json
import os
import subprocess
import sys
import datetime
import argparse
import shutil
import glob
from dotenv import load_dotenv
load_dotenv()
from urllib.parse import urljoin

def eprint(*args, **kwargs):
    """Helper functie om naar stderr te printen."""
    print(*args, file=sys.stderr, **kwargs)

def run_command(command: list, env: dict):
    """Voert een command uit en vangt output en fouten af."""
    process = subprocess.run(command, capture_output=True, text=True, env=env)
    if process.stderr:
        eprint(process.stderr.strip())
    if process.returncode != 0:
        eprint(f"--- Fout bij uitvoeren: {' '.join(command)} ---")
        if process.stdout:
            eprint("--- STDOUT (bij fout) ---")
            eprint(process.stdout.strip())
        raise subprocess.CalledProcessError(process.returncode, command)
    return process

def archive_old_content():
    """Archiveert oude content en data bestanden naar een timestamped map."""
    content_files = glob.glob("content/posts/*.md")
    data_files = ["raw.json", "curated.json", "social_posts.json", "longread_outline.json", "published_post_url.txt"]
    if not content_files and not any(os.path.exists(f) for f in data_files):
        eprint("Geen bestaande content gevonden om te archiveren.")
        return
    
    archive_dir = "archive"
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_archive_dir = os.path.join(archive_dir, timestamp)
    os.makedirs(run_archive_dir)
    
    if content_files:
        posts_archive_dir = os.path.join(run_archive_dir, "content", "posts")
        os.makedirs(posts_archive_dir, exist_ok=True)
        for file_path in content_files:
            shutil.move(file_path, os.path.join(posts_archive_dir, os.path.basename(file_path)))
    
    for file_path in data_files:
        if os.path.exists(file_path):
            shutil.move(file_path, run_archive_dir)

    eprint(f"Oude content gearchiveerd in: {run_archive_dir}")

def get_provider_list():
    """Haalt de lijst van AI providers op uit providers.json."""
    try:
        with open('providers.json', 'r') as f:
            all_providers = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        eprint(f"❌ Kon providers.json niet laden. Fout: {e}")
        return []
    
    forced_provider_id = os.getenv('FORCED_PROVIDER')
    if forced_provider_id and forced_provider_id != 'auto':
        eprint(f"⚡️ Modus: Specifieke provider geforceerd: '{forced_provider_id}'")
        found_provider = next((p for p in all_providers if p['id'] == forced_provider_id), None)
        return [found_provider] if found_provider else []
    return all_providers

def build_script_env(provider_config: dict, content_dir: str) -> dict: 
    """Bouwt de environment dictionary voor subprocessen."""
    script_env = os.environ.copy()
    script_env['AI_API_TYPE'] = provider_config['api_type']
    script_env['AI_MODEL_ID'] = provider_config['model_id']
    script_env['AI_API_KEY'] = os.getenv(provider_config['api_key_name'])
    if provider_config.get('base_url'):
        script_env['AI_BASE_URL'] = provider_config['base_url']
    # Voeg de unieke content directory toe aan de environment
    script_env['VBR_CONTENT_DIR'] = content_dir
    return script_env

def run_task_with_fallback(task_name: str, task_function, providers_to_run):
    """Draait een taak met provider fallback logica."""
    for i, provider_config in enumerate(providers_to_run):
        if not provider_config:
            eprint(f"⚠️ WAARSCHUWING: Ongeldige providerconfiguratie overgeslagen.")
            continue
        
        provider_id = provider_config['id']
        api_key_name = provider_config['api_key_name']
        api_key_value = os.getenv(api_key_name)
        
        eprint("\n" + "="*50)
        eprint(f"POGING {i+1}/{len(providers_to_run)} voor taak '{task_name}': Gebruik provider '{provider_id}'")
        eprint("="*50)
        
        if not api_key_value:
            eprint(f"⚠️ WAARSCHUWING: API-sleutel '{api_key_name}' niet gevonden. Provider wordt overgeslagen.")
            continue
        try:
            result = task_function(provider_config)
            eprint(f"✅ SUCCES: Taak '{task_name}' voltooid met provider '{provider_id}'.")
            return result
        except Exception as e:
            eprint(f"❌ MISLUKT: Taak '{task_name}' gefaald met provider '{provider_id}'. Fout: {e}")
            if i < len(providers_to_run) - 1:
                eprint("Probeer de volgende provider...")
    
    raise RuntimeError(f"DRAMATISCHE FOUT: Kon taak '{task_name}' met geen enkele provider voltooien.")

def write_publication_url(base_url: str, longread_filename: str):
    """Schrijft de volledige URL van de longread naar een bestand."""
    if not base_url:
        eprint("⚠️ WAARSCHUWING: SITE_BASE_URL is niet ingesteld. Kan geen publicatie-URL genereren.")
        return

    path = longread_filename.replace('content/', '', 1).replace('.md', '/')
    full_url = urljoin(base_url, path)
    
    with open("published_post_url.txt", "w", encoding="utf-8") as f:
        f.write(full_url)
    eprint(f"✅ Publicatie-URL voor social media geschreven: {full_url}")

def run_full_pipeline(target_date_str: str or None, no_archive: bool):
    """De hoofd-pipeline die alle stappen voor contentgeneratie coördineert."""
    
    target_date = datetime.date.today()
    if target_date_str:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    target_date_iso = target_date.isoformat()

    providers_to_run = get_provider_list()
    if not providers_to_run:
        eprint("❌ Geen geldige providers gevonden.")
        sys.exit(1)

    run_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    run_content_dir = os.path.join("content", "posts", run_timestamp)
    os.makedirs(run_content_dir, exist_ok=True)
    eprint(f"Content voor deze run wordt opgeslagen in: {run_content_dir}")

    enabled_langs = [lang for lang in json.load(open('languages.json')) if lang.get('enabled')]

    # Stap 1-3: Fetch, Curate, Draft
    if not os.path.exists("raw.json"):
        run_task_with_fallback("Fetch Data", lambda p: run_command(["python3", "-m", "src.fetch", "--date", target_date_iso], env=build_script_env(p)), providers_to_run)
    if not os.path.exists("curated.json"):
        run_command(["python3", "-m", "src.curate"], env=os.environ.copy())
    if not os.path.exists(f"{run_content_dir}/{target_date_iso}_{enabled_langs[0]['code']}.md"):
        run_task_with_fallback("Draft Newsletters", lambda p: run_command(["python3", "-m", "src.draft", "--date", target_date_iso], env=build_script_env(p, run_content_dir)), providers_to_run)

    # Stap 4: Genereer de Engelse outline (één keer)
    if not os.path.exists("longread_outline.json"):
        def task_select_and_generate_outline(provider_config):
            env = build_script_env(provider_config)
            # Stap 4a: Selecteer onderwerp
            topic_process = run_command(["python3", "-m", "src.select_topic"], env=env)
            longread_topic = topic_process.stdout.strip()
            # Stap 4b: Genereer alleen de outline
            run_command(["python3", "-m", "src.generate_longread_outline", longread_topic, "--outline-out", "longread_outline.json"], env=env)
        run_task_with_fallback("Generate Long-Read Outline", task_select_and_generate_outline, providers_to_run)
    else:
        eprint("INFO: Stap 4 (Outline) overgeslagen, bestand bestaat al.")

    # Stap 5: Genereer de longread voor elke actieve taal
    if os.path.exists("longread_outline.json"):
        for lang_config in enabled_langs:
            lang_code = lang_config['code']
            lang_name = lang_config['name']
            output_path = os.path.join(run_content_dir, f"longread_{target_date_iso}_{lang_code}.md")
            if not os.path.exists(output_path):
                def task_generate_article(provider_config):
                    run_command([
                        "python3", "-m", "src.generate_longread", 
                        "--outline-in", "longread_outline.json",
                        "-o", output_path, 
                        "--lang-name", lang_name
                    ], env=build_script_env(provider_config, run_content_dir))
                run_task_with_fallback(f"Generate Long-Read ({lang_name})", task_generate_article, providers_to_run)
            else:
                eprint(f"INFO: Long-read ({lang_name}) overgeslagen, bestand bestaat al.")
    
    # Stap 5.5: Schrijf publicatie-URL (van de Engelse versie)
    longread_filename_en = f"content/posts/longread_{target_date_iso}_en.md"
    if os.path.exists(longread_filename_en) and not os.path.exists("published_post_url.txt"):
        write_publication_url(os.getenv("SITE_BASE_URL"), longread_filename_en)

    # Stap 6: Generate Social Posts
    if not os.path.exists("social_posts.json"):
        run_task_with_fallback("Generate Social Posts", lambda p: run_command(["python3", "-m", "src.generate_social_posts"], env=build_script_env(p)), providers_to_run)

    eprint("\n✅ Pijplijn voor content generatie voltooid.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draait de content generatie pijplijn voor de SSG.")
    parser.add_argument("--date", type=str, help="De datum (YYYY-MM-DD) waarvoor content gegenereerd moet worden.")
    parser.add_argument("--no-archive", action='store_true', help="Sla het archiveren van oude content over.")
    args = parser.parse_args()
    
    run_full_pipeline(args.date, args.no_archive)