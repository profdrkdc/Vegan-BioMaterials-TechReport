# src/publish_ghost.py
import os
import glob
import jwt
import requests
import markdown
from datetime import datetime, timedelta

# ==============================================================================
# De Ghost Admin API implementatie (blijft ongewijzigd)
# ==============================================================================
class GhostAdminAPI:
    def __init__(self, ghost_url, admin_api_key):
        self.ghost_url = ghost_url.rstrip('/')
        self.api_url = f"{self.ghost_url}/ghost/api/admin"
        key_parts = admin_api_key.split(':')
        self.key_id = key_parts[0]
        self.key_secret = key_parts[1]

    def _get_jwt_token(self):
        iat = int(datetime.now().timestamp())
        exp = iat + 300
        payload = {'iat': iat, 'exp': exp, 'aud': '/admin/'}
        token = jwt.encode(
            payload,
            bytes.fromhex(self.key_secret),
            algorithm='HS256',
            headers={'kid': self.key_id}
        )
        return token

    # Deze functie doet maar één ding: een post aanmaken met de data die we geven.
    def create_post(self, post_data):
        token = self._get_jwt_token()
        headers = {'Authorization': f'Ghost {token}'}
        url = f"{self.api_url}/posts/"
        response = requests.post(url, headers=headers, json=post_data)
        response.raise_for_status()
        return response.json()

# ==============================================================================
# De hoofdlogica: Maak één enkele, perfecte DRAFT
# ==============================================================================
if __name__ == "__main__":
    try:
        GHOST_URL = os.environ['GHOST_ADMIN_API_URL']
        GHOST_KEY = os.environ['GHOST_ADMIN_API_KEY']
    except KeyError as e:
        print(f"Error: De omgevingsvariabele {e} is niet ingesteld.")
        exit(1)

    try:
        ghost = GhostAdminAPI(ghost_url=GHOST_URL, admin_api_key=GHOST_KEY)
        print("Ghost Admin API client succesvol geïnitialiseerd.")
    except Exception as e:
        print(f"Fout bij het initialiseren van de Ghost API client: {e}")
        exit(1)

    CONTENT_DIR = "content"
    # We zoeken nu maar naar één bestand om het simpel te houden.
    search_path = os.path.join(CONTENT_DIR, "*_en.md")
    files = glob.glob(search_path)
    
    if not files:
        print(f"Geen Engels .md bestand gevonden in de map {CONTENT_DIR}.")
        exit(0)
    
    # Pak het eerste Engelse bestand dat je vindt
    filepath = files[0]
    print(f"\n--- Verwerken van bestand: {filepath} ---")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
        title = markdown_text.splitlines()[0].strip().replace('# ', '')
    
    html_from_markdown = markdown.markdown(markdown_text)
    
    # Dit is de exacte payload-structuur van de succesvolle test
    post_payload = {
        'posts': [{
            'title': f"DRAFT of: {title}",
            'html': html_from_markdown,
            'status': 'draft' # De cruciale stap: AANMAKEN ALS DRAFT
        }]
    }

    try:
        print("Poging om één enkele DRAFT post aan te maken...")
        ghost.create_post(post_payload)
        print(f"SUCCESS: Draft post '{post_payload['posts'][0]['title']}' succesvol aangemaakt.")
        print("Controleer je Ghost admin panel.")
    except Exception as e:
        print(f"!!! FOUT bij het aanmaken van de draft: {e}")
        import traceback
        traceback.print_exc()