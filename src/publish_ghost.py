# src/publish_ghost.py
import os
import glob
import jwt
import requests
from datetime import datetime, timedelta

# ==============================================================================
# De correcte, handmatige Ghost Admin API implementatie
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
        exp = iat + 300  # Token is 5 minuten geldig
        payload = {'iat': iat, 'exp': exp, 'aud': '/admin/'}
        token = jwt.encode(
            payload,
            bytes.fromhex(self.key_secret),
            algorithm='HS256',
            headers={'kid': self.key_id}
        )
        return token

    def create_post(self, title, markdown_content, status='published', tags=None):
        token = self._get_jwt_token()
        headers = {'Authorization': f'Ghost {token}'}
        
        post_data = {
            'posts': [{
                'title': title,
                'html': markdown_content,  # Ghost kan direct markdown in het html-veld verwerken
                'status': status
            }]
        }
        if tags:
            post_data['posts'][0]['tags'] = [{'name': tag} for tag in tags]
        
        url = f"{self.api_url}/posts/"
        response = requests.post(url, headers=headers, json=post_data)
        response.raise_for_status()  # Stopt het script als er een HTTP-fout is
        return response.json()

# ==============================================================================
# De hoofdlogica van ons script
# ==============================================================================
if __name__ == "__main__":
    # --- Configuratie ---
    try:
        GHOST_URL = os.environ['GHOST_ADMIN_API_URL']
        GHOST_KEY = os.environ['GHOST_ADMIN_API_KEY']
    except KeyError as e:
        print(f"Error: De omgevingsvariabele {e} is niet ingesteld.")
        exit(1)

    CONTENT_DIR = "content"

    # --- Initialiseer de API ---
    try:
        ghost = GhostAdminAPI(ghost_url=GHOST_URL, admin_api_key=GHOST_KEY)
        print("Ghost Admin API client succesvol geïnitialiseerd.")
    except Exception as e:
        print(f"Fout bij het initialiseren van de Ghost API client: {e}")
        exit(1)

    # --- Verwerk bestanden ---
    search_path = os.path.join(CONTENT_DIR, "*.md")
    files = glob.glob(search_path)
    
    if not files:
        print(f"Geen .md bestanden gevonden in de map {CONTENT_DIR}.")
        exit(0)

    for filepath in files:
        print(f"\nVerwerken van bestand: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
            title = markdown_content.splitlines()[0].strip().replace('# ', '')
        
        try:
            ghost.create_post(
                title=title,
                markdown_content=markdown_content,
                status='published',
                tags=['weekly-update']
            )
            print(f"Post '{title}' succesvol gepubliceerd naar Ghost.")
        except Exception as e:
            print(f"!!! Fout bij het publiceren van '{title}': {e}")
            import traceback
            traceback.print_exc()