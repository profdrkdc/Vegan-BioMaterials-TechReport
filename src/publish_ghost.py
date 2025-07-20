# src/publish_ghost.py
import os
import jwt
import requests
import json
from datetime import datetime, timedelta

# ==============================================================================
# De Ghost Admin API implementatie met ingebouwde "zwarte doos" recorder
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
        url = f"{self.api_url}/posts/"

        # --- ZWARTE DOOS: WAT VERSTUREN WE? ---
        print("\n================= ZWARTE DOOS - VERZONDEN DATA ==================")
        print(json.dumps(post_data, indent=2))
        print("=================================================================\n")
        
        response = requests.post(url, headers=headers, json=post_data)
        
        # --- ZWARTE DOOS: WAT KRIJGEN WE TERUG? ---
        print("\n================ ZWARTE DOOS - ONTVANGEN DATA =================")
        print(f"Status Code: {response.status_code}")
        try:
            print("Response Body:")
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            print("Response Body (geen JSON):")
            print(response.text)
        print("=================================================================\n")

        response.raise_for_status() # Stopt als er een HTTP-fout is
        return response.json()

# ==============================================================================
# De hoofdlogica: Maak één enkele, hardgecodeerde DRAFT en neem alles op
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

    hardcoded_title = "API Blackbox Test"
    hardcoded_html_content = "<h2>Test</h2><p>Dit is de content.</p>"

    post_payload = {
        'posts': [{
            'title': hardcoded_title,
            'html': hardcoded_html_content,
            'status': 'draft'
        }]
    }

    try:
        print("Poging om één DRAFT post aan te maken en de communicatie op te nemen...")
        ghost.create_post(post_payload)
        print("SUCCESS: De API call is uitgevoerd. Analyseer de 'ZWARTE DOOS' logs.")
    except Exception as e:
        print(f"!!! FOUT tijdens de API call: {e}")
        import traceback
        traceback.print_exc()