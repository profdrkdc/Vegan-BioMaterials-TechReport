# src/publish_ghost.py
import os
import jwt
import requests
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
# De hoofdlogica: Maak één enkele, hardgecodeerde DRAFT
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

    # --- DE HARDGECODEERDE TEST ---
    print("\n--- Test met hardgecodeerde content ---")

    hardcoded_title = "API Test: Hardcoded Draft"
    hardcoded_html_content = "<h2>Test Content</h2><p>Als je deze tekst kunt lezen, werkt de API-verbinding en het aanmaken van een draft perfect.</p><p>Het probleem ligt dan 100% zeker bij het inlezen of converteren van het .md-bestand.</p>"

    # Dit is de exacte payload-structuur van de succesvolle test
    post_payload = {
        'posts': [{
            'title': hardcoded_title,
            'html': hardcoded_html_content,
            'status': 'draft' # Aanmaken als DRAFT
        }]
    }

    try:
        print("Poging om één DRAFT post aan te maken met hardcoded content...")
        ghost.create_post(post_payload)
        print(f"SUCCESS: Draft post '{hardcoded_title}' zou nu moeten bestaan in Ghost.")
        print("Controleer je Ghost admin panel in de 'Drafts' sectie.")
    except Exception as e:
        print(f"!!! FOUT bij het aanmaken van de hardcoded draft: {e}")
        import traceback
        traceback.print_exc()