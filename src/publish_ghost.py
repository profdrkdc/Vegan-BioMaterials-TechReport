# src/publish_ghost.py
import os
import glob
import jwt
import requests
import markdown
from datetime import datetime

# ==============================================================================
# De Ghost Admin API implementatie (ONGEWIJZIGD)
# ==============================================================================
class GhostAdminAPI:
    # ... (deze klasse is ongewijzigd) ...
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
        token = jwt.encode(payload, bytes.fromhex(self.key_secret), algorithm='HS256', headers={'kid': self.key_id})
        return token
    def _make_request(self, method, endpoint, data=None):
        token = self._get_jwt_token()
        headers = {'Authorization': f'Ghost {token}'}
        url = f"{self.api_url}{endpoint}"
        if method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        response.raise_for_status()
        return response
    def create_post_draft(self, title, html_content, tags=None):
        endpoint = "/posts/?source=html"
        post_data = {'posts': [{'title': title, 'html': html_content, 'status': 'draft'}]}
        if tags:
            post_data['posts'][0]['tags'] = [{'name': tag} for tag in tags]
        response = self._make_request('POST', endpoint, post_data)
        return response.json()['posts'][0]
    def publish_draft(self, post_id, updated_at):
        endpoint = f"/posts/{post_id}/"
        update_data = {'posts': [{'status': 'published', 'updated_at': updated_at}]}
        response = self._make_request('PUT', endpoint, update_data)
        return response.json()['posts'][0]

# ==============================================================================
# De hoofdlogica: Publiceer ALLES in de content map
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
    # --- TERUG NAAR DE SIMPELE, ROBUUSTE LOGICA ---
    search_path = os.path.join(CONTENT_DIR, "*.md")
    print(f"Zoeken naar alle bestanden die voldoen aan: '{search_path}'")
    files_to_publish = glob.glob(search_path)
    
    if not files_to_publish:
        print(f"Geen .md bestanden gevonden in '{CONTENT_DIR}' om te publiceren.")
        exit(0)

    for filepath in files_to_publish:
        print(f"\n--- Verwerken van bestand: {filepath} ---")
        with open(filepath, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
            is_longread = 'longread' in os.path.basename(filepath).lower()
            tag = 'Long Read' if is_longread else 'Weekly Update'
            title = markdown_text.splitlines()[0].strip().replace('# ', '')
        
        html_from_markdown = markdown.markdown(markdown_text)
        
        try:
            print(f"Stap 1: Draft aanmaken voor '{title}' met tag '{tag}'...")
            draft_post = ghost.create_post_draft(title=title, html_content=html_from_markdown, tags=[tag])
            post_id = draft_post['id']
            updated_at = draft_post['updated_at']
            print(f"Draft succesvol aangemaakt met ID: {post_id}")

            print(f"Stap 2: Publiceren van post ID {post_id}...")
            published_post = ghost.publish_draft(post_id, updated_at)
            print(f"SUCCESS: Post '{published_post['title']}' is nu gepubliceerd!")

        except Exception as e:
            print(f"!!! FOUT bij het verwerken van '{title}': {e}")
            import traceback
            traceback.print_exc()