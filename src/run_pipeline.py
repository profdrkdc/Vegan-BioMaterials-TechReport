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
    """Print berichten naar de standaard error stream."""
    print(*args, file=sys.stderr, **kwargs)

def run_command(command: list, env: dict):
    """Voert een shell commando uit en handelt fouten af."""
    process = subprocess.run(command, capture_output=True, text=True, env=env)
    if process.returncode != 0:
        eprint(f"--- Fout bij uitvoeren: {' '.join(command)} ---")
        eprint("STDOUT:", process.stdout)
        eprint("STDERR:", process.stderr)
        raise subprocess.CalledProcessError(process.returncode, command)
    return process

def archive_old_content():
    """
    CORRECTIE: Volledige implementatie.
    Verplaatst bestaande content (.md) en databestanden (.json) naar de archiefmap.
    """
    CONTENT_DIR = "content"
    ARCHIVE_DIR = "archive"
    
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    files_to_archive = []
    # Zoek naar alle .md bestanden in de content map
    content_files = glob.glob(os.path.join(CONTENT_DIR, "*.md"))
    files_to_archive.extend(content_files)
    
    # Voeg de root data-bestanden toe om te archiveren
    for data_file in ["raw.json", "curated.json"]:
        if os.path.exists(data_file):
            files_to_archive.append(data_file)
            
    if not files_to_archive:
        eprint("Geen bestaande content gevonden om te archiveren.")
        return

    eprint(f"Archiveren van {len(files_to_archive)} oud(e) bestand(en)...")
    for filepath in files_to_archive:
        try:
            shutil.move(filepath, os.path.join(ARCHIVE_DIR, os.path.basename(filepath)))
        except Exception as e:
            eprint(f"⚠️ Kon '{filepath}' niet archiveren. Fout: {e}")

def get_provider_list():
    """Leest providers.json en stelt de failover-volgorde in."""
    try:
        with open('providers.json', 'r') as f:
            all_providers = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        eprint(f"❌ Kon providers.json niet laden. Fout: {e}")
        return []

    # De 'PREFERRED_PROVIDER' logica is nu overbodig in de workflow,
    # maar blijft nuttig voor lokale tests. Het script valt terug op de
    # standaardvolgorde als de variabele niet is ingesteld.
    preferred_provider_id = os.getenv('PREFERRED_PROVIDER')
    if preferred_provider_id:
        eprint(f"🔄 Modus: Voorkeur voor '{preferred_provider_id}' met automatische failover.")
        preferred_provider = next((p for p in all_providers if p['id'] == preferred_provider_id), None)
        if preferred_provider:
            other_providers = [p for p in all_providers if p['id'] != preferred_provider_id]
            return [preferred_provider] + other_providers
    
    eprint("🔄 Modus: Standaard automatische failover (volgens providers.json).")
    return all_providers

def run_task(task_function, providers_to_run):
    """Probeert een taakfunctie uit te voeren met een lijst van providers."""
    for i, provider_config in enumerate(providers_to_run):
        provider_id = provider_config['id']
        api_key_name = provider_config['api_key_name']
        api_key_value = os.getenv(api_key_name)

        eprint("\n" + "="*50)
        eprint(f"POGING {i+1}/{len(providers_to_run)} voor taak: Gebruik provider '{provider_id}'")
        eprint("="*50)

        if not api_key_value:
            eprint(f"⚠️ WAARSCHUWING: API-sleutel '{api_key_name}' niet gevonden. Provider wordt overgeslagen.")
            continue
        
        try:
            result = task_function(provider_config)
            eprint(f"✅ SUCCES: Taak voltooid met provider '{provider_id}'.")
            return provider_config, result
        except Exception as e:
            eprint(f"❌ MISLUKT: Taak gefaald met provider '{provider_id}'.")
            # Toon de fout voor betere debugging
            import traceback
            traceback.print_exc(file=sys.stderr)
            if i < len(providers_to_run) - 1:
                eprint("Probeer de volgende provider...")
    
    return None, None

def run_full_pipeline(target_date_str: str or None, no_archive: bool):
    """De hoofd-pijplijn die alle taken sequentieel uitvoert."""
    if not no_archive:
        archive_old_content()
    
    target_date = datetime.date.today()
    if target_date_str:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    target_date_iso = target_date.isoformat()

    providers_to_run = get_provider_list()
    if not providers_to_run:
        eprint("❌ Geen geldige providers gevonden. Pijplijn stopt.")
        sys.exit(1)

    # --- TAAK 1: Genereer de Nieuwsbrief ---
    def generate_newsletter_task(provider_config):
        script_env = os.environ.copy()
        # CORRECTIE: Zorg ervoor dat AI_BASE_URL altijd een string is.
        script_env.update({
            'AI_API_TYPE': provider_config['api_type'],
            'AI_MODEL_ID': provider_config['model_id'],
            'AI_API_KEY': os.getenv(provider_config['api_key_name']),
            'AI_BASE_URL': provider_config.get('base_url') or ""
        })
        run_command(["python3", "-m", "src.fetch", "--date", target_date_iso], env=script_env)
        run_command(["python3", "-m", "src.curate"], env=script_env)
        run_command(["python3", "-m", "src.draft", "--date", target_date_iso], env=script_env)
        return True

    successful_provider, newsletter_success = run_task(generate_newsletter_task, providers_to_run)

    if not newsletter_success:
        eprint("\n❌ FATALE FOUT: Kon met geen enkele provider de nieuwsbrief genereren.")
        sys.exit(1)

    # --- TAAK 2: Genereer de Long-Read ---
    def generate_longread_task(provider_config):
        script_env = os.environ.copy()
        # CORRECTIE: Zorg ervoor dat AI_BASE_URL altijd een string is.
        script_env.update({
            'AI_API_TYPE': provider_config['api_type'],
            'AI_MODEL_ID': provider_config['model_id'],
            'AI_API_KEY': os.getenv(provider_config['api_key_name']),
            'AI_BASE_URL': provider_config.get('base_url') or ""
        })
        
        eprint("\n--- Sub-stap 2a: Selecteer Long-Read Onderwerp ---")
        process = run_command(["python3", "-m", "src.select_topic"], env=script_env)
        longread_topic = process.stdout.strip()

        if not longread_topic:
            raise ValueError("Kon geen long-read onderwerp selecteren.")
        
        eprint("\n--- Sub-stap 2b: Genereer Long-Read Artikel ---")
        longread_filename = f"content/longread_{target_date_iso}_en.md"
        run_command(["python3", "-m", "src.generate_longread", longread_topic, "-o", longread_filename], env=script_env)
        return True

    # VERBETERING: Maak een correct geroteerde failover-lijst.
    successful_provider_index = providers_to_run.index(successful_provider)
    longread_providers = providers_to_run[successful_provider_index:] + providers_to_run[:successful_provider_index]
    
    _, longread_success = run_task(generate_longread_task, longread_providers)

    if not longread_success:
        eprint("\n⚠️ WAARSCHUWING: Kon geen long-read genereren. De nieuwsbrief is wel gelukt.")
    
    eprint("\n✅ Pijplijn voltooid.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voert de volledige contentpijplijn uit.")
    parser.add_argument('--date', type=str, help="Optionele datum (YYYY-MM-DD) om de pijplijn voor te draaien.")
    parser.add_argument('--no_archive', action='store_true', help="Sla het archiveren van oude content over.")
    args = parser.parse_args()

    try:
        run_full_pipeline(target_date_str=args.date, no_archive=args.no_archive)
    except Exception as e:
        eprint(f"\n\n--- EEN ONVERWACHTE FOUT HEEFT DE PIJPLIJN GESTOPT ---")
        eprint(f"Fout: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)