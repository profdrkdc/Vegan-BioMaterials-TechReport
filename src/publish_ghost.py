# src/publish_ghost.py
import os
import glob
import jwt
import requests
import markdown # We hebben de markdown-conversie weer nodig
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

    def create_post(self, post_data):
        token = self._get_jwt_token()
        headers = {'Authorization': f'Ghost {token}'}
        
        # De bewezen, werkende URL
        url = f"{self.api_url}/posts/?source=html"
        
        response = requests.post(url, headers=headers, json=post_data)
        response.raise_for_status()
        return response.json()

# ==============================================================================
# De hoofdlogica: Maak drafts aan op basis van de .md bestanden
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
    search_path = os.path.join(CONTENT_DIR, "*.md")
    files = glob.glob(search_path)
    
    if not files:
        print(f"Geen .md bestanden gevonden in de map {CONTENT_DIR}.")
        exit(0)

    for filepath in files:
        print(f"\n--- Verwerken van bestand: {filepath} ---")
        with open(filepath, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
            title = markdown_text.splitlines()[0].strip().replace('# ', '')
        
        # Converteer de markdown naar HTML
        html_from_markdown = markdown.markdown(markdown_text)
        
        # Bouw de payload op basis van de werkende test
        post_payload = {
            'posts': [{
                'title': title,
                'html': html_from_markdown,
                'status': 'draft'
            }]
        }

        try:
            print(f"Poging om een DRAFT post aan te maken voor '{title}'...")
            ghost.create_post(post_payload)
            print(f"SUCCESS: Draft post '{title}' succesvol aangemaakt.")
        except Exception as e:
            print(f"!!! FOUT bij het aanmaken van de draft: {e}")
            import traceback
            traceback.print_exc()

    print("\nAlle bestanden zijn verwerkt. Controleer je 'Drafts' in Ghost.")