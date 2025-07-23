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
    # ... (deze functie blijft ongewijzigd)

def get_provider_list():
    """Leest providers.json en stelt de failover-volgorde in."""
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
    
    eprint("🔄 Modus: Standaard automatische failover.")
    return all_providers

def run_task(task_function, providers_to_run):
    """Probeert een taakfunctie uit te voeren met de lijst van providers."""
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
            # Voer de specifieke taakfunctie uit
            result = task_function(provider_config)
            eprint(f"✅ SUCCES: Taak voltooid met provider '{provider_id}'.")
            # Geef de succesvolle provider en het resultaat terug
            return provider_config, result
        except Exception as e:
            eprint(f"❌ MISLUKT: Taak gefaald met provider '{provider_id}'. Fout: {e}")
            if i < len(providers_to_run) - 1:
                eprint("Probeer de volgende provider...")
    
    # Als de loop eindigt zonder succes
    return None, None

def run_full_pipeline(target_date_str: str or None, no_archive: bool):
    if not no_archive:
        archive_old_content()
    
    # ... (datumlogica is ongewijzigd)
    target_date = datetime.date.today()
    if target_date_str:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    target_date_iso = target_date.isoformat()

    providers_to_run = get_provider_list()
    if not providers_to_run:
        eprint("❌ Geen geldige providers gevonden om de pijplijn mee te draaien.")
        sys.exit(1)

    # --- TAAK 1: Genereer de Nieuwsbrief ---
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
        return True # Simpel succes signaal

    successful_provider, newsletter_success = run_task(generate_newsletter_task, providers_to_run)

    if not newsletter_success:
        eprint("\n❌ DRAMATISCHE FOUT: Kon met geen enkele provider de nieuwsbrief genereren.")
        sys.exit(1)

    # --- TAAK 2: Genereer de Long-Read ---
    def generate_longread_task(provider_config):
        script_env = os.environ.copy()
        script_env['AI_API_TYPE'] = provider_config['api_type']
        script_env['AI_MODEL_ID'] = provider_config['model_id']
        script_env['AI_API_KEY'] = os.getenv(provider_config['api_key_name'])
        if provider_config.get('base_url'):
            script_env['AI_BASE_URL'] = provider_config['base_url']

        # Selecteer eerst het onderwerp
        eprint("\n--- Sub-stap 2a: Select Topic ---")
        process = run_command(["python3", "-m", "src.select_topic"], env=script_env)
        longread_topic = process.stdout.strip()

        if not longread_topic:
            eprint("⚠️ WAARSCHUWING: Kon geen long-read onderwerp selecteren met deze provider.")
            # We retourneren None om aan te geven dat deze provider de taak niet kon voltooien
            return None
        
        # Genereer dan het artikel
        eprint("\n--- Sub-stap 2b: Generate Long-Read Article ---")
        longread_filename = f"content/longread_{target_date_iso}_en.md"
        run_command(["python3", "-m", "src.generate_longread", longread_topic, "-o", longread_filename], env=script_env)
        return True

    # Maak een nieuwe failover-lijst die begint met de provider die de nieuwsbrief heeft gemaakt
    longread_providers = [p for p in providers_to_run if p['id'] == successful_provider['id']]
    longread_providers.extend([p for p in providers_to_run if p['id'] != successful_provider['id']])
    
    _, longread_success = run_task(generate_longread_task, longread_providers)

    if not longread_success:
        eprint("\n⚠️ WAARSCHUWING: Kon met geen enkele provider een long-read artikel genereren, maar de nieuwsbrief is wel gelukt.")
    
    eprint("\n✅ Pijplijn voltooid.")

if __name__ == "__main__":
    # ... (de __main__ sectie blijft ongewijzigd)