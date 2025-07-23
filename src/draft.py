import os
import json
from datetime import datetime
from .ai_provider import generate_content
from .utils import load_config, get_project_root

def load_enabled_languages():
    """
    Leest languages.json en retourneert een lijst van talen
    waarvan 'enabled' op true staat.
    """
    root_dir = get_project_root()
    languages_path = os.path.join(root_dir, 'languages.json')
    try:
        with open(languages_path, 'r', encoding='utf-8') as f:
            all_languages = json.load(f)
        return [lang for lang in all_languages if lang.get('enabled', False)]
    except FileNotFoundError:
        print("Error: languages.json not found in the project root.")
        return []
    except json.JSONDecodeError:
        print("Error: Could not decode languages.json. Please check for syntax errors.")
        return []

def create_newsletter_draft(keywords):
    """
    Genereert een nieuwsbrief-concept in meerdere talen op basis van languages.json.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    config = load_config()
    providers = config.get('providers', [])

    enabled_languages = load_enabled_languages()
    if not enabled_languages:
        print("No enabled languages found. Aborting newsletter generation.")
        return

    print(f"Gevonden talen om te genereren: {[lang['name'] for lang in enabled_languages]}")

    for lang_config in enabled_languages:
        lang_code = lang_config['code']
        lang_name = lang_config['name']
        edition_word = lang_config['edition_word']
        
        print(f"--- Start generatie voor {lang_name} ({lang_code}) ---")

        prompt = (
            f"Je bent een expert in veganisme en biotechnologie. "
            f"Schrijf een boeiende, informatieve en inspirerende nieuwsbrief in het {lang_name}. "
            f"De toon is professioneel maar toegankelijk. Gebruik markdown voor de opmaak. "
            f"De nieuwsbrief moet de volgende secties bevatten: Introductie, Nieuwsoverzicht, "
            f"Product Spotlight, en een Afsluiting. "
            f"Focus op de volgende trefwoorden: {', '.join(keywords)}. "
            f"Begin de nieuwsbrief met een hoofdtitel: '# Vegan BioTech Report: {edition_word} {today_str}'"
        )

        try:
            content = generate_content(prompt, providers)
            
            if content:
                output_dir = os.path.join(get_project_root(), 'content')
                os.makedirs(output_dir, exist_ok=True)
                
                # Bestandsnaam bevat nu de taalcode
                file_name = f"{today_str}_{lang_code}.md"
                file_path = os.path.join(output_dir, file_name)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Succesvol nieuwsbrief-concept opgeslagen voor {lang_name} in: {file_path}")
            else:
                print(f"Kon geen content genereren voor {lang_name}.")

        except Exception as e:
            print(f"Een fout is opgetreden tijdens het genereren voor {lang_name}: {e}")
        
        print(f"--- Einde generatie voor {lang_name} ---")

if __name__ == '__main__':
    # Voorbeeld-trefwoorden voor directe uitvoering
    sample_keywords = ["cell-based meat", "precision fermentation", "plant-based innovation"]
    create_newsletter_draft(sample_keywords)