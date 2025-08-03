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

def build_script_env(provider_config: dict) -> dict:
    """Bouwt de environment dictionary voor subprocessen."""
    script_env = os.environ.copy()
    script_env['AI_API_TYPE'] = provider_config['api_type']
    script_env['AI_MODEL_ID'] = provider_config['model_id']
    script_env['AI_API_KEY'] = os.getenv(provider_config['api_key_name'])
    if provider_config.get('base_url'):
        script_env['AI_BASE_URL'] = provider_config['base_url']
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
    if not no_archive:
        archive_old_content()
    
    target_date = datetime.date.today()
    if target_date_str:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    target_date_iso = target_date.isoformat()

    providers_to_run = get_provider_list()
    if not providers_to_run:
        eprint("❌ Geen geldige providers gevonden.")
        sys.exit(1)

    # Stap 1: Fetch
    if not os.path.exists("raw.json"):
        def task_fetch(provider_config):
            run_command(["python3", "-m", "src.fetch", "--date", target_date_iso], env=build_script_env(provider_config))
        run_task_with_fallback("Fetch Data", task_fetch, providers_to_run)
    else:
        eprint("INFO: Stap 1 (Fetch) overgeslagen, 'raw.json' bestaat al.")

    # Stap 2: Curate
    if not os.path.exists("curated.json"):
        eprint("\n" + "="*50 + "\nINFO: Stap 2 (Curate) uitvoeren...\n" + "="*50)
        run_command(["python3", "-m", "src.curate"], env=os.environ.copy())
    else:
        eprint("INFO: Stap 2 (Curate) overgeslagen, 'curated.json' bestaat al.")

    # Stap 3: Draft
    enabled_langs = [lang for lang in json.load(open('languages.json')) if lang.get('enabled')]
    draft_files_exist = all(os.path.exists(f"content/posts/{target_date_iso}_{lang['code']}.md") for lang in enabled_langs)
    if not draft_files_exist:
        def task_draft(provider_config):
            run_command(["python3", "-m", "src.draft", "--date", target_date_iso], env=build_script_env(provider_config))
        run_task_with_fallback("Draft Newsletters", task_draft, providers_to_run)
    else:
        eprint("INFO: Stap 3 (Draft) overgeslagen, alle nieuwsbrieven bestaan al.")

    # Stap 4 & 5: Select Topic & Generate Longread
    longread_filename_en = f"content/posts/longread_{target_date_iso}_en.md"
    if not os.path.exists(longread_filename_en):
        if not os.path.exists("longread_outline.json"):
            def task_select_topic(provider_config):
                process = run_command(["python3", "-m", "src.select_topic"], env=build_script_env(provider_config))
                return process.stdout.strip()
            longread_topic = run_task_with_fallback("Select Topic", task_select_topic, providers_to_run)
            
            def task_generate_longread(provider_config):
                run_command([
                    "python3", "-m", "src.generate_longread", 
                    longread_topic, 
                    "-o", longread_filename_en,
                    "--outline-out", "longread_outline.json"
                ], env=build_script_env(provider_config))
            run_task_with_fallback("Generate Longread", task_generate_longread, providers_to_run)
        else:
            eprint("INFO: Stap 4/5 (Longread) overgeslagen, outline bestaat al maar .md niet. U kunt het .md bestand handmatig verwijderen om opnieuw te genereren.")
    else:
        eprint("INFO: Stap 4/5 (Longread) overgeslagen, long-read bestand bestaat al.")
    
    # Stap 5.5: Schrijf publicatie-URL
    if os.path.exists(longread_filename_en) and not os.path.exists("published_post_url.txt"):
        write_publication_url(os.getenv("SITE_BASE_URL"), longread_filename_en)

    # Stap 6: Generate Social Posts
    if not os.path.exists("social_posts.json"):
        if os.path.exists("longread_outline.json"):
            def task_generate_social(provider_config):
                run_command(["python3", "-m", "src.generate_social_posts"], env=build_script_env(provider_config))
            run_task_with_fallback("Generate Social Posts", task_generate_social, providers_to_run)
        else:
            eprint("INFO: Stap 6 (Social Posts) overgeslagen, geen longread outline gevonden.")
    else:
        eprint("INFO: Stap 6 (Social Posts) overgeslagen, 'social_posts.json' bestaat al.")

    eprint("\n✅ Pijplijn voor content generatie voltooid.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draait de content generatie pijplijn voor de SSG.")
    parser.add_argument("--date", type=str, help="De datum (YYYY-MM-DD) waarvoor content gegenereerd moet worden.")
    parser.add_argument("--no-archive", action='store_true', help="Sla het archiveren van oude content over.")
    args = parser.parse_args()
    
    run_full_pipeline(args.date, args.no_archive)