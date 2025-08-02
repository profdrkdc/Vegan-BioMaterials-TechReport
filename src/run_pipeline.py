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
    # Zoek nu in de posts submap
    content_files = glob.glob("content/posts/*.md")
    data_files = ["raw.json", "curated.json", "social_posts.json", "longread_outline.json"]
    if not content_files and not any(os.path.exists(f) for f in data_files):
        eprint("Geen bestaande content gevonden om te archiveren.")
        return
    
    archive_dir = "archive"
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_archive_dir = os.path.join(archive_dir, timestamp)
    os.makedirs(run_archive_dir)
    
    # Verplaats eerst de content bestanden
    if content_files:
        os.makedirs(os.path.join(run_archive_dir, "content", "posts"), exist_ok=True)
        for file_path in content_files:
            shutil.move(file_path, os.path.join(run_archive_dir, file_path))
    
    # Verplaats daarna de data bestanden
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
            return result # Geef het resultaat terug (bijv. stdout van een commando)
        except Exception as e:
            eprint(f"❌ MISLUKT: Taak '{task_name}' gefaald met provider '{provider_id}'. Fout: {e}")
            if i < len(providers_to_run) - 1:
                eprint("Probeer de volgende provider...")
    
    # Als alle providers falen, gooi dan een fout op
    raise RuntimeError(f"DRAMATISCHE FOUT: Kon taak '{task_name}' met geen enkele provider voltooien.")

def run_full_pipeline(target_date_str: str or None, no_archive: bool, skip_content_generation: bool, skip_social_publish: bool):
    """De hoofd-pipeline die alle stappen coördineert."""
    if not no_archive and not skip_content_generation:
        archive_old_content()
    
    target_date = datetime.date.today()
    if target_date_str:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    target_date_iso = target_date.isoformat()

    providers_to_run = get_provider_list()
    if not providers_to_run:
        eprint("❌ Geen geldige providers gevonden.")
        sys.exit(1)

    # --- START VAN GRANULAIRE STAPPEN ---
    
    # Stap 1: Fetch
    if os.path.exists("raw.json"):
        eprint("INFO: Stap 1 (Fetch) overgeslagen, 'raw.json' bestaat al.")
    else:
        def task_fetch(provider_config):
            run_command(["python3", "-m", "src.fetch", "--date", target_date_iso], env=build_script_env(provider_config))
        run_task_with_fallback("Fetch Data", task_fetch, providers_to_run)

    # Stap 2: Curate (geen AI nodig)
    if os.path.exists("curated.json"):
        eprint("INFO: Stap 2 (Curate) overgeslagen, 'curated.json' bestaat al.")
    else:
        eprint("\n" + "="*50 + "\nINFO: Stap 2 (Curate) uitvoeren...\n" + "="*50)
        run_command(["python3", "-m", "src.curate"], env=os.environ.copy())

    # Stap 3: Draft
    draft_en_path = f"content/posts/{target_date_iso}_en.md"
    if os.path.exists(draft_en_path):
        eprint("INFO: Stap 3 (Draft) overgeslagen, nieuwsbrieven bestaan al.")
    else:
        def task_draft(provider_config):
            run_command(["python3", "-m", "src.draft", "--date", target_date_iso], env=build_script_env(provider_config))
        run_task_with_fallback("Draft Newsletters", task_draft, providers_to_run)

    # Stap 4: Select Topic
    def task_select_topic(provider_config):
        process = run_command(["python3", "-m", "src.select_topic"], env=build_script_env(provider_config))
        return process.stdout.strip()
    longread_topic = run_task_with_fallback("Select Topic", task_select_topic, providers_to_run)
    
    # Stap 5: Generate Longread
    longread_filename_en = f"content/posts/longread_{target_date_iso}_en.md"
    if os.path.exists(longread_filename_en):
        eprint("INFO: Stap 5 (Generate Longread) overgeslagen, long-read bestaat al.")
    elif longread_topic:
        def task_generate_longread(provider_config):
            run_command([
                "python3", "-m", "src.generate_longread", 
                longread_topic, 
                "-o", longread_filename_en,
                "--outline-out", "longread_outline.json"
            ], env=build_script_env(provider_config))
        run_task_with_fallback("Generate Longread", task_generate_longread, providers_to_run)
    else:
        eprint("⚠️ WAARSCHUWING: Stap 5 (Generate Longread) overgeslagen, geen onderwerp geselecteerd.")

    # Stap 6: Generate Social Posts
    if os.path.exists("social_posts.json"):
        eprint("INFO: Stap 6 (Generate Social Posts) overgeslagen, 'social_posts.json' bestaat al.")
    else:
        def task_generate_social(provider_config):
            run_command(["python3", "-m", "src.generate_social_posts"], env=build_script_env(provider_config))
        run_task_with_fallback("Generate Social Posts", task_generate_social, providers_to_run)

    # Stap 7: Publiceren naar sociale media (optioneel)
    if not skip_social_publish:
        def task_publish_social(provider_config):
            run_command(["python3", "-m", "src.publish_social"], env=build_script_env(provider_config))
        run_task_with_fallback("Publish Social Posts", task_publish_social, providers_to_run)
    else:
        eprint("INFO: Publicatie naar sociale media overgeslagen vanwege --skip-social-publish vlag.")
    
    eprint("\n✅ Pijplijn voor content generatie voltooid.")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Draait de content generatie pijplijn voor de SSG.")
    parser.add_argument("--date", type=str, help="De datum (YYYY-MM-DD) waarvoor content gegenereerd moet worden.")
    parser.add_argument("--no-archive", action='store_true', help="Sla het archiveren van oude content over.")
    parser.add_argument("--skip-content-generation", action='store_true', help="Sla de content generatie stappen over.") # Deze wordt nu genegeerd door de logica, maar laten we hem staan voor compatibiliteit.
    parser.add_argument("--skip-social-publish", action='store_true', help="Sla de publicatie naar sociale media over.")
    args = parser.parse_args()
    
    run_full_pipeline(
        args.date, 
        args.no_archive, 
        args.skip_content_generation, 
        args.skip_social_publish
    )