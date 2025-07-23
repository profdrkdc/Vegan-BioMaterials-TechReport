# src/run_pipeline.py
import json
import os
import subprocess
import sys
import datetime

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

def run_full_pipeline():
    try:
        with open('providers.json', 'r') as f:
            providers = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        eprint(f"❌ Kon providers.json niet laden. Fout: {e}")
        sys.exit(1)

    # Controleer of een specifieke provider is geforceerd
    forced_provider_id = os.getenv('FORCED_PROVIDER')
    providers_to_run = []

    if forced_provider_id and forced_provider_id != 'auto':
        eprint(f"⚡️ Modus: Specifieke provider geforceerd: '{forced_provider_id}'")
        # Zoek de geforceerde provider in de configuratie
        found_provider = next((p for p in all_providers if p['id'] == forced_provider_id), None)
        if found_provider:
            providers_to_run.append(found_provider)
        else:
            eprint(f"❌ Fout: Geforceerde provider '{forced_provider_id}' niet gevonden in providers.json.")
            sys.exit(1)
    else:
        eprint("🔄 Modus: Automatische failover (alle providers worden geprobeerd)")
        providers_to_run = all_providers
        
    success = False
    for i, provider_config in enumerate(providers):
        provider_id = provider_config['id']
        api_key_name = provider_config['api_key_name']
        api_key_value = os.getenv(api_key_name)

        eprint("="*50)
        eprint(f"POGING {i+1}/{len(providers)}: Gebruik provider '{provider_id}' (Model: {provider_config['model_id']})")
        eprint("="*50)

        if not api_key_value:
            eprint(f"⚠️ WAARSCHUWING: API-sleutel '{api_key_name}' niet gevonden. Provider '{provider_id}' wordt overgeslagen.")
            continue

        try:
            # Maak een schone environment voor de subprocessen
            script_env = os.environ.copy()
            script_env['AI_API_TYPE'] = provider_config['api_type']
            script_env['AI_MODEL_ID'] = provider_config['model_id']
            script_env['AI_API_KEY'] = api_key_value
            if provider_config['base_url']:
                script_env['AI_BASE_URL'] = provider_config['base_url']

            eprint("\n--- Stap 1: Fetch, Curate, Draft ---")
            run_command(["python3", "-m", "src.fetch"], env=script_env)
            run_command(["python3", "-m", "src.curate"], env=script_env)
            run_command(["python3", "-m", "src.draft"], env=script_env)

            eprint("\n--- Stap 2: Select Topic ---")
            process = run_command(["python3", "-m", "src.select_topic"], env=script_env)
            longread_topic = process.stdout.strip()
            
            if not longread_topic:
                eprint("⚠️ WAARSCHUWING: Kon geen long-read onderwerp selecteren. Sla artikelgeneratie over.")
            else:
                eprint("\n--- Stap 3: Generate Long-Read ---")
                longread_filename = f"content/longread_{datetime.date.today().isoformat()}_en.md"
                run_command(["python3", "-m", "src.generate_longread", longread_topic, "-o", longread_filename], env=script_env)
            
            eprint(f"\n✅ SUCCES: Pijplijn voltooid met provider '{provider_id}'.")
            success = True
            break

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            eprint(f"❌ MISLUKT: Pijplijn gefaald met provider '{provider_id}'.")
            eprint("Probeer de volgende provider...")

    if not success:
        eprint("\n" + "="*50)
        eprint("❌ DRAMATISCHE FOUT: Alle providers zijn gefaald. De workflow stopt.")
        eprint("="*50)
        sys.exit(1)

if __name__ == "__main__":
    run_full_pipeline()