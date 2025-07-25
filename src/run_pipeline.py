# src/run_pipeline.py

import json
import os
import subprocess
import sys
import datetime
import argparse
import shutil
import glob

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def run_command(command: list, env: dict):
    process = subprocess.run(command, capture_output=True, text=True, env=env)
    if process.returncode != 0:
        eprint(f"--- Fout bij uitvoeren: {' '.join(command)} ---")
        eprint("STDOUT:", process.stdout)
        eprint("STDERR:", process.stderr)
        raise subprocess.CalledProcessError(process.returncode, command)
    return process

def archive_old_content():
    content_files = glob.glob("content/*.md")
    data_files = ["raw.json", "curated.json", "social_posts.json"] # social_posts.json toegevoegd
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
    try:
        with open('providers.json', 'r') as f:
            all_providers = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        eprint(f"❌ Kon providers.json niet laden. Fout: {e}")
        return []
    forced_provider_id = os.getenv('FORCED_PROVIDER')
    preferred_provider_id = os.getenv('PREFERRED_PROVIDER')
    if forced_provider_id and forced_provider_id != 'auto':
        eprint(f"⚡️ Modus: Specifieke provider geforceerd: '{forced_provider_id}'")
        found_provider = next((p for p in all_providers if p['id'] == forced_provider_id), None)
        return [found_provider] if found_provider else []
    if preferred_provider_id:
        eprint(f"🔄 Modus: Branch-voorkeur '{preferred_provider_id}' met automatische failover.")
        preferred_provider = next((p for p in all_providers if p['id'] == preferred_provider_id), None)
        if preferred_provider:
            other_providers = [p for p in all_providers if p['id'] != preferred_provider_id]
            return [preferred_provider] + other_providers
    eprint("🔄 Modus: Standaard automatische failover (volgens providers.json).")
    return all_providers

def run_task(task_name: str, task_function, providers_to_run):
    for i, provider_config in enumerate(providers_to_run):
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

def run_full_pipeline(target_date_str: str or None, no_archive: bool):
    if not no_archive:
        archive_old_content()
    
    target_date = datetime.date.today()
    if target_date_str:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    target_date_iso = target_date.isoformat()

    providers_to_run = get_provider_list()
    if not providers_to_run:
        eprint("❌ Geen geldige providers gevonden om de pijplijn mee te draaien.")
        sys.exit(1)

    # TAAK 1: Genereer de Nieuwsbrief
    def generate_newsletter_task(provider_config):
        script_env = os.environ.copy()
        script_env['AI_API_TYPE'] = provider_config['api_type']
        script_env['AI_MODEL_ID'] = provider_config['model_id']
        script_env['AI_API_KEY'] = os.getenv(provider_config['api_key_name'])
        if provider_config.get('base_url'):
            script_env['AI_BASE_URL'] = provider_config['base_url']
        run_command(["python3", "-m", "src.fetch", "--date", target_date_iso], env=script_env)
        run_command(["python3", "-m", "src.curate"], env=script_env)
        run_command(["python3", "-m", "src.draft", "--date", target_date_iso], env=script_env)
        return True

    successful_provider, newsletter_success = run_task(
        "Nieuwsbrief Generatie", generate_newsletter_task, providers_to_run
    )

    if not newsletter_success:
        eprint("\n❌ DRAMATISCHE FOUT: Kon met geen enkele provider de nieuwsbrief genereren.")
        sys.exit(1)

    # TAAK 2: Genereer en Vertaal de Long-Read
    def generate_longread_task(provider_config):
        script_env = os.environ.copy()
        script_env['AI_API_TYPE'] = provider_config['api_type']
        script_env['AI_MODEL_ID'] = provider_config['model_id']
        script_env['AI_API_KEY'] = os.getenv(provider_config['api_key_name'])
        if provider_config.get('base_url'):
            script_env['AI_BASE_URL'] = provider_config['base_url']
        eprint("\n--- Sub-stap 2a: Selecteer Long-Read Onderwerp ---")
        process = run_command(["python3", "-m", "src.select_topic"], env=script_env)
        longread_topic = process.stdout.strip()
        if not longread_topic:
            eprint("⚠️ WAARSCHUWING: Kon geen long-read onderwerp selecteren met deze provider.")
            return None
        eprint("\n--- Sub-stap 2b: Genereer Engels Long-Read Artikel ---")
        longread_filename_en = f"content/longread_{target_date_iso}_en.md"
        run_command(["python3", "-m", "src.generate_longread", longread_topic, "-o", longread_filename_en], env=script_env)
        eprint("\n--- Sub-stap 2c: Vertaal Long-Read naar andere talen ---")
        try:
            with open('languages.json', 'r', encoding='utf-8') as f:
                languages = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            eprint(f"⚠️ WAARSCHUWING: Kon 'languages.json' niet laden, vertalingen worden overgeslagen. Fout: {e}")
            return True
        active_languages = [lang for lang in languages if lang.get("enabled")]
        for lang_config in active_languages:
            if lang_config['code'] == 'en':
                continue
            lang_code = lang_config['code']
            lang_name = lang_config['name']
            eprint(f"Vertalen naar {lang_name} ({lang_code})...")
            longread_filename_lang = f"content/longread_{target_date_iso}_{lang_code}.md"
            try:
                run_command([
                    "python3", "-m", "src.translate_longread",
                    longread_filename_en,
                    longread_filename_lang,
                    "--lang_name", lang_name
                ], env=script_env)
            except Exception as e:
                eprint(f"⚠️ Fout bij vertalen naar {lang_name}: {e}. Deze taal wordt overgeslagen.")
                continue
        return True

    longread_providers = [p for p in providers_to_run if p['id'] == successful_provider['id']]
    longread_providers.extend([p for p in providers_to_run if p['id'] != successful_provider['id']])
    
    _, longread_success = run_task(
        "Long-Read Generatie & Vertaling", generate_longread_task, longread_providers
    )

    if not longread_success:
        eprint("\n⚠️ WAARSCHUWING: Kon met geen enkele provider een long-read artikel genereren, maar de nieuwsbrief is wel gelukt.")
    
    # --- TAAK 3: Genereer Social Media Posts ---
    eprint("\n--- Starten van Taak 3: Social Media Post Generatie ---")
    def generate_socials_task(provider_config):
        script_env = os.environ.copy()
        script_env['AI_API_TYPE'] = provider_config['api_type']
        script_env['AI_MODEL_ID'] = provider_config['model_id']
        script_env['AI_API_KEY'] = os.getenv(provider_config['api_key_name'])
        if provider_config.get('base_url'):
            script_env['AI_BASE_URL'] = provider_config['base_url']
        
        run_command(["python3", "-m", "src.generate_social_posts"], env=script_env)
        return True

    social_providers = longread_providers 

    _, social_posts_success = run_task(
        "Social Media Generatie", generate_socials_task, social_providers
    )

    if not social_posts_success:
        eprint("\n⚠️ WAARSCHUWING: Kon met geen enkele provider social media posts genereren.")

    eprint("\n✅ Pijplijn voltooid.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draait de volledige content generatie pijplijn.")
    parser.add_argument("--date", type=str, help="De datum (YYYY-MM-DD) waarvoor de content moet worden gegenereerd.")
    parser.add_argument("--no_archive", action='store_true', help="Sla het archiveren van oude content over.")
    args = parser.parse_args()
    run_full_pipeline(args.date, args.no_archive)