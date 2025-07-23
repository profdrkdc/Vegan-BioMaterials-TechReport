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
    """Helper functie om naar stderr te printen."""
    print(*args, file=sys.stderr, **kwargs)

def run_command(command: list, env: dict):
    """Voert een shell commando uit en stopt bij een fout."""
    process = subprocess.run(command, capture_output=True, text=True, env=env)
    if process.returncode != 0:
        eprint(f"--- Fout bij uitvoeren: {' '.join(command)} ---")
        eprint("STDOUT:", process.stdout)
        eprint("STDERR:", process.stderr)
        raise subprocess.CalledProcessError(process.returncode, command)
    return process

# ==============================================================================
# DE AANGEPASTE FUNCTIE STAAT HIER
# ==============================================================================
def archive_old_content():
    """Verplaatst alle .md bestanden van content/ naar content_archive/."""
    source_dir = "content"
    archive_dir = "content_archive"
    
    # Stap 1: Zorg ervoor dat beide mappen bestaan.
    # Dit voorkomt fouten als de content map leeg was en door Git werd verwijderd.
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(archive_dir, exist_ok=True)
    
    # Stap 2: Zoek naar alle .md bestanden in de bronmap.
    files_to_move = glob.glob(os.path.join(source_dir, "*.md"))
    
    if not files_to_move:
        eprint("Geen oude content gevonden in 'content/' om te archiveren.")
        return

    eprint(f"Archiveren van {len(files_to_move)} oud(e) bestand(en) van '{source_dir}' naar '{archive_dir}'...")
    
    # Stap 3: Verplaats elk bestand individueel.
    for file_path in files_to_move:
        try:
            basename = os.path.basename(file_path)
            destination_path = os.path.join(archive_dir, basename)
            
            # Voeg een timestamp toe als een bestand met dezelfde naam al bestaat in het archief.
            if os.path.exists(destination_path):
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                name, ext = os.path.splitext(basename)
                destination_path = os.path.join(archive_dir, f"{name}_{timestamp}{ext}")
            
            shutil.move(file_path, destination_path)
        except Exception as e:
            eprint(f"Kon bestand {file_path} niet verplaatsen: {e}")
            
    eprint("Archiveren voltooid. De 'content' map is nu leeg.")

# ==============================================================================
# DE REST VAN HET SCRIPT IS ONGEWIJZIGD
# ==============================================================================
def run_full_pipeline(target_date_str: str or None, no_archive: bool):
    """Leest de provider-configuratie en probeert de pijplijn voor elke provider."""
    if not no_archive:
        archive_old_content()
    else:
        eprint("Archiveringsstap overgeslagen zoals gevraagd (--no-archive).")

    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
            eprint(f"Speciale run: Datum ingesteld op {target_date.isoformat()}")
        except ValueError:
            eprint(f"❌ Ongeldig datumformaat: '{target_date_str}'. Gebruik YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = datetime.date.today()
        eprint(f"Standaard run: Datum is vandaag, {target_date.isoformat()}")
    
    target_date_iso = target_date.isoformat()

    try:
        with open('providers.json', 'r') as f:
            all_providers = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        eprint(f"❌ Kon providers.json niet laden. Fout: {e}")
        sys.exit(1)

    
    forced_provider_id = os.getenv('FORCED_PROVIDER')
    preferred_provider_id = os.getenv('PREFERRED_PROVIDER')
    providers_to_run = []

    if forced_provider_id and forced_provider_id != 'auto':
        eprint(f"⚡️ Modus: Specifieke provider geforceerd: '{forced_provider_id}'")
        found_provider = next((p for p in all_providers if p['id'] == forced_provider_id), None)
        if found_provider:
            providers_to_run.append(found_provider)
        else:
            eprint(f"❌ Fout: Geforceerde provider '{forced_provider_id}' niet gevonden in providers.json.")
            sys.exit(1)
    elif preferred_provider_id:
        eprint(f"🔄 Modus: Branch-voorkeur '{preferred_provider_id}' met automatische failover.")
        # Zoek de voorkeursprovider
        preferred_provider = next((p for p in all_providers if p['id'] == preferred_provider_id), None)
        if preferred_provider:
            # Voeg de voorkeursprovider als eerste toe
            providers_to_run.append(preferred_provider)
            # Voeg alle andere providers toe die niet de voorkeursprovider zijn
            other_providers = [p for p in all_providers if p['id'] != preferred_provider_id]
            providers_to_run.extend(other_providers)
        else:
            eprint(f"⚠️ Waarschuwing: Voorkeursprovider '{preferred_provider_id}' niet gevonden, gebruik standaard failover.")
            providers_to_run = all_providers
    else:
        eprint("🔄 Modus: Standaard automatische failover (geplande run).")
        providers_to_run = all_providers
        

    success = False
    for i, provider_config in enumerate(providers_to_run):
        provider_id = provider_config['id']
        api_key_name = provider_config['api_key_name']
        api_key_value = os.getenv(api_key_name)

        eprint("\n" + "="*50)
        eprint(f"POGING {i+1}/{len(providers_to_run)}: Gebruik provider '{provider_id}' (Model: {provider_config['model_id']})")
        eprint("="*50)

        if not api_key_value:
            eprint(f"⚠️ WAARSCHUWING: API-sleutel '{api_key_name}' niet gevonden. Provider '{provider_id}' wordt overgeslagen.")
            continue

        try:
            script_env = os.environ.copy()
            script_env['AI_API_TYPE'] = provider_config['api_type']
            script_env['AI_MODEL_ID'] = provider_config['model_id']
            script_env['AI_API_KEY'] = api_key_value
            if provider_config.get('base_url'):
                script_env['AI_BASE_URL'] = provider_config['base_url']

            eprint("\n--- Sub-stap 1: Fetch, Curate, Draft ---")
            run_command(["python3", "-m", "src.fetch", "--date", target_date_iso], env=script_env)
            run_command(["python3", "-m", "src.curate"], env=script_env)
            run_command(["python3", "-m", "src.draft", "--date", target_date_iso], env=script_env)

            eprint("\n--- Sub-stap 2: Select Topic ---")
            process = run_command(["python3", "-m", "src.select_topic"], env=script_env)
            longread_topic = process.stdout.strip()
            
            if not longread_topic:
                eprint("⚠️ WAARSCHUWING: Kon geen long-read onderwerp selecteren. Sla artikelgeneratie over.")
            elif "structured_output" not in provider_config.get("capabilities", []):
                eprint(f"⚠️ WAARSCHUWING: Provider '{provider_id}' ondersteunt geen gestructureerde output. Sla artikelgeneratie over.")
            else:
                eprint("\n--- Sub-stap 3: Generate Long-Read ---")
                longread_filename = f"content/longread_{target_date_iso}_en.md"
                run_command(["python3", "-m", "src.generate_longread", longread_topic, "-o", longread_filename], env=script_env)
            
            eprint(f"\n✅ SUCCES: Pijplijn voltooid met provider '{provider_id}'.")
            success = True
            break

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            eprint(f"❌ MISLUKT: Pijplijn gefaald met provider '{provider_id}'.")
            if i < len(providers_to_run) - 1:
                eprint("Probeer de volgende provider...")

    if not success:
        eprint("\n" + "="*50)
        eprint("❌ DRAMATISCHE FOUT: Alle providers zijn gefaald. De workflow stopt.")
        eprint("="*50)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrator voor de content pipeline.")
    parser.add_argument('--no-archive', action='store_true', help="Sla het archiveren van oude content over.")
    parser.add_argument('--date', type=str, help="Gebruik een specifieke datum (YYYY-MM-DD) i.p.v. vandaag.")
    
    args = parser.parse_args()
    run_full_pipeline(target_date_str=args.date, no_archive=args.no_archive)