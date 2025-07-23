import os
import glob
from datetime import datetime
from .ghost_client import GhostAdminAPI
from .utils import get_project_root

def get_language_code_from_filename(filepath):
    """
    Extraheert de taalcode uit een bestandsnaam zoals '2025-07-23_nl.md'.
    Retourneert 'EN' als de code niet gevonden kan worden, als veilige fallback.
    """
    try:
        # Neemt de bestandsnaam, splitst op '_' en pakt het een-na-laatste deel.
        # Vervolgens wordt de extensie .md verwijderd.
        filename = os.path.basename(filepath)
        code = filename.split('_')[-1].split('.')[0]
        # Controleer of de code een redelijke lengte heeft (bv. 2 of 3 letters)
        if 2 <= len(code) <= 3 and code.isalpha():
            return code.upper()
    except IndexError:
        pass # Fallback wordt hieronder afgehandeld
    print(f"Waarschuwing: kon taalcode niet afleiden uit '{filepath}'. Gebruik 'EN' als fallback.")
    return 'EN'

def publish_newsletters_to_ghost():
    """
    Vindt alle nieuwsbrieven van vandaag, voegt een taaltag toe en publiceert ze naar Ghost.
    """
    root_dir = get_project_root()
    content_dir = os.path.join(root_dir, 'content')
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Gebruik een glob-patroon om alle taalversies van vandaag te vinden
    newsletter_files = glob.glob(os.path.join(content_dir, f"{today_str}_*.md"))

    if not newsletter_files:
        print("Geen nieuwsbriefbestanden gevonden om te publiceren voor vandaag.")
        return

    ghost = GhostAdminAPI() # Initialiseert de client

    for filepath in newsletter_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # De titel is de eerste regel van de markdown (bv. '# Vegan BioTech Report: ...')
        title = content.split('\n', 1)[0].lstrip('# ').strip()
        
        lang_code_tag = get_language_code_from_filename(filepath)
        
        # Voeg de basis-tag en de dynamische taal-tag toe
        tags = ['Weekly Update', lang_code_tag]
        
        print(f"Publiceren van '{title}' met tags {tags}...")
        
        try:
            response = ghost.create_post(title, content, tags)
            if response and 'id' in response['posts'][0]:
                print(f"Succesvol gepubliceerd: {title}")
            else:
                print(f"Fout bij publiceren van {title}. Reactie: {response}")
        except Exception as e:
            print(f"Kon post '{title}' niet maken via Ghost API: {e}")

if __name__ == '__main__':
    publish_newsletters_to_ghost()