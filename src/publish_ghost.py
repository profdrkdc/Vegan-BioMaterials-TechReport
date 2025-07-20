# src/publish_ghost.py
import os
import glob
from ghost_client import Ghost

# --- Configuratie ---
try:
    GHOST_URL = os.environ['GHOST_ADMIN_API_URL']
    # De 'ghost-client' bibliotheek splitst de API key in een ID en een SECRET,
    # gescheiden door een dubbele punt.
    GHOST_KEY = os.environ['GHOST_ADMIN_API_KEY']
    GHOST_ADMIN_ID, GHOST_ADMIN_SECRET = GHOST_KEY.split(':')
except KeyError as e:
    print(f"Error: De omgevingsvariabele {e} is niet ingesteld.")
    exit(1)
except ValueError:
    print("Error: GHOST_ADMIN_API_KEY heeft niet het juiste formaat. Moet 'id:secret' zijn.")
    exit(1)

CONTENT_DIR = "content"

# --- Hoofdlogica ---
if __name__ == "__main__":
    # Initialiseer de Ghost API
    try:
        ghost = Ghost(
            GHOST_URL,
            client_id=GHOST_ADMIN_ID,
            client_secret=GHOST_ADMIN_SECRET
        )
        print("Succesvol verbonden met de Ghost API.")
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
            content = f.read()

        try:
            # Maak een nieuwe post aan
            ghost.posts.create(
                title='Titel wordt automatisch uit Markdown gehaald',
                custom_excerpt='Gepubliceerd via GitHub Action',
                markdown=content,
                status='published',
                tags=['weekly-update'] # Optioneel
            )
            print(f"Post van bestand '{filepath}' succesvol gepubliceerd.")

        except Exception as e:
            print(f"Fout bij het publiceren van '{filepath}': {e}")
            # Print de volledige error voor meer details
            import traceback
            traceback.print_exc()