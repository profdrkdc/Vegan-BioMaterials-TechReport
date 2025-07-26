# src/publish_ghost.py
import os
import sys
import glob
import jwt
import requests
import markdown
import time
from datetime import datetime

class GhostAdminAPI:
    def __init__(self, ghost_url, admin_api_key):
        self.ghost_url = ghost_url.rstrip('/')
        self.api_url = f"{self.ghost_url}/ghost/api/admin"
        key_parts = admin_api_key.split(':')
        self.key_id = key_parts
        self.key_secret = key_parts
    def _get_jwt_token(self):
        iat = int(datetime.now().timestamp())
        exp = iat + 300
        payload = {'iat': iat, 'exp': exp, 'aud': '/admin/'}
        token = jwt.encode(payload, bytes.fromhex(self.key_secret), algorithm='HS256', headers={'kid': self.key_id})
        return token
    def _make_request(self, method, endpoint, data=None):
        token = self._get_jwt_token()
        headers = {'Authorization': f'Ghost {token}'}
        url = f"{self.api_url}{endpoint}"
        response = requests.request(method, url, headers=headers, json=data)
        response.raise_for_status()
        return response
    def create_post_draft(self, title, html_content, tags=None):
        endpoint = "/posts/?source=html"
        post_data = {'posts': [{'title': title, 'html': html_content, 'status': 'draft'}]}
        if tags:
            post_data['posts']['tags'] = [{'name': tag} for tag in tags]
        response = self._make_request('POST', endpoint, post_data)
        return response.json()['posts']
    def publish_draft(self, post_id, updated_at):
        endpoint = f"/posts/{post_id}/"
        update_data = {'posts': [{'status': 'published', 'updated_at': updated_at}]}
        response = self._make_request('PUT', endpoint, update_data)
        return response.json()['posts']

if __name__ == "__main__":
    try:
        GHOST_URL = os.environ['GHOST_ADMIN_API_URL']
        GHOST_KEY = os.environ['GHOST_ADMIN_API_KEY']
    except KeyError as e:
        print(f"Error: Omgevingsvariabele {e} is niet ingesteld.", file=sys.stderr)
        exit(1)

    try:
        ghost = GhostAdminAPI(ghost_url=GHOST_URL, admin_api_key=GHOST_KEY)
        print("Ghost Admin API client succesvol geïnitialiseerd.")
    except Exception as e:
        print(f"Fout bij initialiseren van de Ghost API client: {e}", file=sys.stderr)
        exit(1)

    CONTENT_DIR = "content"
    MAX_RETRIES = 3
    RETRY_DELAY = 10

    files_to_publish = glob.glob(os.path.join(CONTENT_DIR, "*.md"))
    
    if not files_to_publish:
        print(f"Geen .md bestanden gevonden in '{CONTENT_DIR}' om te publiceren.")
        exit(0)

    for filepath in files_to_publish:
        print(f"\n--- Verwerken van bestand: {filepath} ---")
        filename = os.path.basename(filepath)
        
        base_tag = 'Long Read' if 'longread' in filename.lower() else 'Weekly Update'
        lang_code = filename.split('_')[-1].split('.')
        lang_tag = lang_code.upper()
        final_tags = [base_tag, lang_tag]

        with open(filepath, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
            title = markdown_text.splitlines().strip().replace('# ', '')
        
        html_from_markdown = markdown.markdown(markdown_text)
        
        for attempt in range(MAX_RETRIES):
            try:
                print(f"Poging {attempt + 1}/{MAX_RETRIES}: Draft aanmaken voor '{title}'...")
                draft_post = ghost.create_post_draft(title=title, html_content=html_from_markdown, tags=final_tags)
                post_id = draft_post['id']
                updated_at = draft_post['updated_at']
                print(f"Draft succesvol aangemaakt met ID: {post_id}")

                print(f"Publiceren van post ID {post_id}...")
                published_post = ghost.publish_draft(post_id, updated_at)
                print(f"SUCCESS: Post '{published_post['title']}' is nu gepubliceerd!")
                break
            except requests.exceptions.RequestException as e:
                print(f"!!! FOUT (Poging {attempt + 1}) bij API-aanroep voor '{title}': {e}", file=sys.stderr)
                if attempt + 1 == MAX_RETRIES:
                    print(f"!!! DEFINITIEVE FOUT: Kon '{title}' niet publiceren.", file=sys.stderr)
                else:
                    print(f"Wacht {RETRY_DELAY} seconden voor de volgende poging...")
                    time.sleep(RETRY_DELAY)
            except Exception as e:
                print(f"!!! ONVERWACHTE FOUT bij '{title}': {e}", file=sys.stderr)
                break