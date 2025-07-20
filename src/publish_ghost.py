# src/publish_ghost.py
import os
import glob
from ghost_admin_api import GhostAdminAPI

# --- Configuratie ---
try:
    GHOST_URL = os.environ['GHOST_ADMIN_API_URL']
    GHOST_KEY = os.environ['GHOST_ADMIN_API_KEY']
except KeyError as e:
    print(f"Error: De omgevingsvariabele {e} is niet ingesteld.")
    exit(1)

CONTENT_DIR = "content"

# --- Hoofdlogica ---
if __name__ == "__main__":
    # Initialiseer de Ghost API
    try:
        ghost = GhostAdminAPI(
            url=GHOST_URL,
            key=GHOST_KEY,
            version="v5.0"
        )
        print("Succesvol verbonden met de Ghost Admin API.")
    except Exception as e:
        print(f"Fout bij het verbinden met de Ghost API: {e}")
        exit(1)

    # Vind alle .md bestanden in de content map
    search_path = os.path.join(CONTENT_DIR, "*.md")
    files = glob.glob(search_path)
    
    if not files:
        print(f"Geen .md bestanden gevonden in de map {CONTENT_DIR}.")
        exit(0)

    for filepath in files:
        print(f"\nVerwerken van bestand: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Haal titel eruit (eerste regel, zonder '# ')
        title = lines[0].strip().replace('# ', '')
        # De rest is de body
        html_content = "".join(lines)
        
        try:
            # Maak een nieuwe post aan
            response = ghost.posts.create({
                'title': title,
                'html': html_content, # Ghost accepteert direct Markdown/HTML
                'status': 'published', # Zet op 'draft' als je het eerst wilt reviewen
                # 'tags': ['news', 'weekly-update'] # Optioneel: voeg tags toe
            })
            print(f"Post '{title}' succesvol gepubliceerd naar Ghost.")

        except Exception as e:
            print(f"Fout bij het publiceren van '{title}': {e}")