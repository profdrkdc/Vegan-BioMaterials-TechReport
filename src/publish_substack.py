import os
import glob
from substack import Api
from substack.post import Post

# --- Configuratie ---
try:
    SUBSTACK_EMAIL = os.environ['SUBSTACK_EMAIL']
    SUBSTACK_PASSWORD = os.environ['SUBSTACK_PASSWORD']
    SUBSTACK_PUBLICATION_URL = os.environ['SUBSTACK_PUBLICATION_URL']
except KeyError as e:
    print(f"Error: De omgevingsvariabele {e} is niet ingesteld.")
    exit(1)

CONTENT_DIR = "content"
TARGET_LANGUAGE = "_en.md"

# --- Functies ---
def find_markdown_file():
    """Zoekt naar het Engelse markdown-bestand in de content-map."""
    search_path = os.path.join(CONTENT_DIR, f"*{TARGET_LANGUAGE}")
    files = glob.glob(search_path)
    if not files:
        print(f"Error: Geen bestand gevonden dat eindigt op {TARGET_LANGUAGE} in de map {CONTENT_DIR}.")
        return None
    latest_file = max(files, key=os.path.getmtime)
    print(f"Bestand gevonden: {latest_file}")
    return latest_file

def read_markdown_content(filepath):
    """Leest de volledige inhoud van het markdown-bestand."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

# --- Hoofdlogica ---
if __name__ == "__main__":
    markdown_file = find_markdown_file()
    if markdown_file:
        markdown_content = read_markdown_content(markdown_file)
        
        # De bibliotheek kan zelf de titel uit de markdown halen als het begint met #
        # We hoeven het dus niet apart te parsen.

        try:
            print("Authenticatie bij Substack...")
            api = Api(
                email=SUBSTACK_EMAIL,
                password=SUBSTACK_PASSWORD,
                publication_url=SUBSTACK_PUBLICATION_URL
            )
            print("Authenticatie succesvol.")

            # Maak een draft van de post
            # De library verwacht de content als een lijst van secties.
            # Voor een simpele markdown post is één sectie met type 'markdown' voldoende.
            post_draft_data = {
                'type': 'markdown',
                'content': markdown_content
            }
            
            # De `post.add_draft` methode creëert de draft en haalt de titel uit de markdown.
            draft = api.add_draft(post_draft_data)
            draft_id = draft.get("id")

            if not draft_id:
                print("Fout: Kon geen draft aanmaken.")
                print("Ontvangen data:", draft)
                exit(1)

            print(f"Draft succesvol aangemaakt met ID: {draft_id}")

            # Publiceer de draft
            print("Publiceren van de draft...")
            result = api.publish_draft(draft_id)
            print("Post succesvol gepubliceerd!")
            print("Resultaat:", result)

        except Exception as e:
            print(f"Er is een fout opgetreden: {e}")
            exit(1)
