# src/publish_ghost.py
import os
import glob
import jwt
import requests
import json
from datetime import datetime, timedelta

# ==============================================================================
# De Ghost Admin API implementatie
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

    # Een 'rauwe' create-functie die precies verstuurt wat we meegeven
    def create_post_raw(self, post_data):
        token = self._get_jwt_token()
        headers = {'Authorization': f'Ghost {token}'}
        url = f"{self.api_url}/posts/?source=html"
        response = requests.post(url, headers=headers, json=post_data)
        response.raise_for_status()
        return response.json()

# ==============================================================================
# De hoofdlogica: Het Experiment
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

    # --- Definitie van de Experimenten ---
    test_content_markdown = "## Test Content\n\nThis is de **markdown** content van de test."
    test_content_html = "<h2>Test Content</h2><p>This is de <b>HTML</b> content van de test.</p>"
    
    # JSON-structuur voor MobileDoc (oudere Ghost versies)
    mobiledoc_payload = json.dumps({
        "version": "0.3.1", "markups": [], "atoms": [],
        "cards": [["markdown", {"markdown": "This is content in a **MobileDoc** card."}]]
    })
    
    # JSON-structuur voor Lexical (moderne Ghost versies)
    lexical_payload = json.dumps({
        "root": {"children": [{"children": [{"detail": 0, "format": 0, "mode": "normal", "style": "", "text": "This is content in the Lexical format.", "type": "text", "version": 1}], "direction": "ltr", "format": "", "indent": 0, "type": "paragraph", "version": 1}], "direction": "ltr", "format": "", "indent": 0, "type": "root", "version": 1}
    })

    tests = [
        {
            "name": "HTML Field Test",
            "data": {"posts": [{"title": "API Test: HTML Field", "html": test_content_html}]}
        },
        {
            "name": "Markdown Field Test",
            "data": {"posts": [{"title": "API Test: Markdown Field", "markdown": test_content_markdown}]}
        },
        {
            "name": "MobileDoc Field Test",
            "data": {"posts": [{"title": "API Test: MobileDoc Field", "mobiledoc": mobiledoc_payload}]}
        },
        {
            "name": "Lexical Field Test",
            "data": {"posts": [{"title": "API Test: Lexical Field", "lexical": lexical_payload}]}
        }
    ]

    # --- Voer de Experimenten uit ---
    for test in tests:
        print(f"\n--- Running: {test['name']} ---")
        try:
            ghost.create_post_raw(test['data'])
            print(f"SUCCESS: Post '{test['data']['posts'][0]['title']}' succesvol aangemaakt.")
        except Exception as e:
            print(f"FAILURE: Kon post niet aanmaken voor test '{test['name']}'.")
            print(f"Error: {e}")

    print("\nAlle tests zijn voltooid. Controleer je Ghost admin panel om te zien welke posts de juiste content hebben.")