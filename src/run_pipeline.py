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
    print(*args, file=sys.stderr, **kwargs)

def run_command(command: list, env: dict):
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

def run_full_pipeline(target_date_str: str or None, no_archive: bool, skip_content_generation: bool, skip_blogger_publish: bool, skip_social_publish: bool):
    # Debugging: Check PUBLISH_BLOGGER env var
    eprint(f"DEBUG: PUBLISH_BLOGGER env var: {os.getenv('PUBLISH_BLOGGER')}")

    # --- DE AANPASSING IS HIER ---
    # Voer alleen archivering uit als we NIET in publish-only modus zijn.
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
        script_env = build_script_env(provider_config)

        # Stap 1: Fetch
        raw_json_path = "raw.json"
        if os.path.exists(raw_json_path):
            eprint(f"INFO: '{raw_json_path}' bestaat al. Overslaan van src.fetch.")
        else:
            run_command(["python3", "-m", "src.fetch", "--date", target_date_iso], env=script_env)

        # Stap 2: Curate
        curated_json_path = "curated.json"
        if os.path.exists(curated_json_path):
            eprint(f"INFO: '{curated_json_path}' bestaat al. Overslaan van src.curate.")
        else:
            run_command(["python3", "-m", "src.curate"], env=script_env)

        # Stap 3: Draft
        draft_en_path = f"content/{target_date_iso}_en.md"
        draft_nl_path = f"content/{target_date_iso}_nl.md"
        if os.path.exists(draft_en_path) and os.path.exists(draft_nl_path):
            eprint(f"INFO: '{draft_en_path}' en '{draft_nl_path}' bestaan al. Overslaan van src.draft.")
        else:
            run_command(["python3", "-m", "src.draft", "--date", target_date_iso], env=script_env)

        # Stap 4: Select Topic (kan niet worden overgeslagen op basis van bestandsbestaan)
        process = run_command(["python3", "-m", "src.select_topic"], env=script_env)
        longread_topic = process.stdout.strip()

        # Stap 5: Generate Longread
        longread_filename_en = f"content/longread_{target_date_iso}_en.md"
        longread_outline_filename = "longread_outline.json"
        if longread_topic:
            if os.path.exists(longread_filename_en) and os.path.exists(longread_outline_filename):
                eprint(f"INFO: '{longread_filename_en}' en '{longread_outline_filename}' bestaan al. Overslaan van src.generate_longread.")
            else:
                run_command([
                    "python3", "-m", "src.generate_longread", 
                    longread_topic, 
                    "-o", longread_filename_en,
                    "--outline-out", longread_outline_filename
                ], env=script_env)
        else:
             eprint("⚠️ WAARSCHUWING: Kon geen long-read onderwerp selecteren.")

        # Stap 6: Generate Social Posts
        social_posts_json_path = "social_posts.json"
        if os.path.exists(social_posts_json_path):
            eprint(f"INFO: '{social_posts_json_path}' bestaat al. Overslaan van src.generate_social_posts.")
        else:
            run_command(["python3", "-m", "src.generate_social_posts"], env=script_env)
        return True

    def publish_social_task(provider_config):
        if not os.path.exists("social_posts.json"):
            eprint("❌ FOUT: 'social_posts.json' niet gevonden. Draai eerst de pipeline zonder --publish-social.")
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

    # Nieuwe stap: Publiceren naar Blogger
    if not skip_blogger_publish and os.getenv('PUBLISH_BLOGGER', 'false').lower() == 'true':
        eprint("INFO: Starten met publicatie naar Blogger...")
        # Zoek het gegenereerde longread-bestand
        longread_files = glob.glob(f"content/longread_{target_date_iso}_en.md")
        if longread_files:
            longread_file_path = longread_files[0]
            try:
                from src.publish_blogger import create_post as create_blogger_post
                import json
                
                with open("longread_outline.json", 'r', encoding='utf-8') as f:
                    outline_data = json.load(f)
                title = outline_data['title']

                with open(longread_file_path, 'r', encoding='utf-8') as f:
                    content_md = f.read()
                
                # Converteer Markdown naar HTML voor Blogger
                import markdown
                html_content = markdown.markdown(content_md)
                
                create_blogger_post(title, html_content)
                eprint("✅ SUCCES: Long-read gepubliceerd op Blogger.")
            except Exception as e:
                eprint(f"❌ FOUT: Publicatie naar Blogger is mislukt. Fout: {e}")
                # We stoppen de pijplijn niet als alleen de publicatie mislukt
        else:
            eprint("⚠️ WAARSCHUWING: Geen long-read bestand gevonden om te publiceren naar Blogger.")
    elif skip_blogger_publish:
        eprint("INFO: Publicatie naar Blogger overgeslagen vanwege --skip-blogger-publish vlag.")
    elif os.getenv('PUBLISH_BLOGGER', 'false').lower() == 'false':
        eprint("INFO: Publicatie naar Blogger overgeslagen omdat PUBLISH_BLOGGER niet 'true' is.")

    if not skip_social_publish and not skip_content_generation:
        _, publish_success = run_task("Social Media Publicatie", publish_social_task, providers_to_run)
        if not publish_success:
            eprint("❌ DRAMATISCHE FOUT: Kon met geen enkele provider de social posts publiceren.")
            sys.exit(1)
    elif skip_social_publish:
        eprint("INFO: Social media publicatie overgeslagen vanwege --skip-social-publish vlag.")
    
    eprint("✅ Pijplijn voltooid.")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Draait de volledige content generatie pijplijn.")
    parser.add_argument("--date", type=str, help="De datum (YYYY-MM-DD) waarvoor content gegenereerd moet worden.")
    parser.add_argument("--no-archive", action='store_true', help="Sla het archiveren van oude content over.")
    parser.add_argument("--skip-content-generation", action='store_true', help="Sla de content generatie stappen over.")
    parser.add_argument("--skip-blogger-publish", action='store_true', help="Sla de publicatie naar Blogger over.")
    parser.add_argument("--skip-social-publish", action='store_true', help="Sla de publicatie naar sociale media over.")
    args = parser.parse_args()
    eprint(f"DEBUG: Parsed arguments: {args}")
    
    run_full_pipeline(args.date, args.no_archive, args.skip_content_generation, args.skip_blogger_publish, args.skip_social_publish)