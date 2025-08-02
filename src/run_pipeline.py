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
    content_files = glob.glob("content/*.md")
    data_files = ["raw.json", "curated.json", "social_posts.json", "longread_outline.json"]
    if not content_files and not any(os.path.exists(f) for f in data_files):
        eprint("Geen bestaande content gevonden om te archiveren.")
        return
    
    archive_dir = "archive"
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_archive_dir = os.path.join(archive_dir, timestamp)
    os.makedirs(run_archive_dir)
    
    for file_path in content_files + data_files:
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

def run_task(task_name: str, task_function, providers_to_run):
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
            return provider_config, result
        except Exception as e:
            eprint(f"❌ MISLUKT: Taak '{task_name}' gefaald met provider '{provider_id}'. Fout: {e}")
            if i < len(providers_to_run) - 1:
                eprint("Probeer de volgende provider...")
    return None, None

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

    def generate_content_task(provider_config):
        """Taak voor het genereren van alle content- en databestanden."""
        script_env = build_script_env(provider_config)
        
        # Stappen 1 t/m 6: Fetch, Curate, Draft, Select Topic, Generate Longread, Generate Social Posts
        run_command(["python3", "-m", "src.fetch", "--date", target_date_iso], env=script_env)
        run_command(["python3", "-m", "src.curate"], env=script_env)
        run_command(["python3", "-m", "src.draft", "--date", target_date_iso], env=script_env)
        
        process = run_command(["python3", "-m", "src.select_topic"], env=script_env)
        longread_topic = process.stdout.strip()
        
        if longread_topic:
            run_command([
                "python3", "-m", "src.generate_longread", 
                longread_topic, 
                "-o", f"content/longread_{target_date_iso}_en.md",
                "--outline-out", "longread_outline.json"
            ], env=script_env)
        else:
             eprint("⚠️ WAARSCHUWING: Kon geen long-read onderwerp selecteren.")

        run_command(["python3", "-m", "src.generate_social_posts"], env=script_env)
        return True

    def publish_social_task(provider_config):
        """Taak voor het publiceren naar sociale media."""
        if not os.path.exists("social_posts.json"):
            eprint("❌ FOUT: 'social_posts.json' niet gevonden.")
            raise FileNotFoundError("social_posts.json niet gevonden.")
        
        script_env = build_script_env(provider_config)
        run_command(["python3", "-m", "src.publish_social"], env=script_env)
        return True

    # --- Hoofdlogica van de pipeline ---
    if not skip_content_generation:
        _, content_success = run_task("Content Generatie", generate_content_task, providers_to_run)
        if not content_success:
            eprint("❌ DRAMATISCHE FOUT: Kon met geen enkele provider de content genereren.")
            sys.exit(1)
    else:
        eprint("INFO: Content generatie overgeslagen vanwege --skip-content-generation vlag.")

    # Social media publicatie (optioneel)
    if not skip_social_publish:
        _, publish_success = run_task("Social Media Publicatie", publish_social_task, providers_to_run)
        if not publish_success:
            eprint("⚠️ WAARSCHUWING: Kon social posts niet publiceren (dit stopt de pipeline niet).")
    else:
        eprint("INFO: Social media publicatie overgeslagen vanwege --skip-social-publish vlag.")
    
    eprint("\n✅ Pijplijn voor content generatie voltooid.")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Draait de content generatie pijplijn voor de SSG.")
    parser.add_argument("--date", type=str, help="De datum (YYYY-MM-DD) waarvoor content gegenereerd moet worden.")
    parser.add_argument("--no-archive", action='store_true', help="Sla het archiveren van oude content over.")
    parser.add_argument("--skip-content-generation", action='store_true', help="Sla de content generatie stappen over.")
    parser.add_argument("--skip-social-publish", action='store_true', help="Sla de publicatie naar sociale media over.")
    args = parser.parse_args()
    
    run_full_pipeline(
        args.date, 
        args.no_archive, 
        args.skip_content_generation, 
        args.skip_social_publish
    )