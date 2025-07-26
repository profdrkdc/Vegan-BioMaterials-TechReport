# src/publish_ghost.py
import os
import sys
import glob
import jwt
import requests
import markdown
import time
from datetime import datetime
from dotenv import load_dotenv

# --- CONFIGURATIE ---
URL_OUTPUT_FILE = "published_post_url.txt"
# --------------------

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
        token = jwt.encode(payload, bytes.fromhex(self.key_secret), algorithm='HS256', headers={'kid': self.key_id})
        return token
    def _make_request(self, method, endpoint, data=None):
        token = self._get_jwt_token()
        headers = {'Authorization': f'Ghost {token}'}
        url = f"{self.api_url}{endpoint}"
        response = requests.request(method, url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    def create_post(self, title, html_content, tags=None):
        endpoint = "/posts/?source=html"
        post_data = {'posts': [{'title': title, 'html': html_content, 'status': 'published'}]}
        if tags:
            post_data['posts'][0]['tags'] = [{'name': tag} for tag in tags]
        response_data = self._make_request('POST', endpoint, post_data)
        return response_data['posts'][0]

if __name__ == "__main__":
    load_dotenv()
    
    try:
        GHOST_URL = os.environ['GHOST_ADMIN_API_URL']
        GHOST_KEY = os.environ['GHOST_ADMIN_API_KEY']
    except KeyError as e:
        print(f"Error: Omgevingsvariabele {e} is niet ingesteld.", file=sys.stderr)
        exit(1)

    ghost = GhostAdminAPI(ghost_url=GHOST_URL, admin_api_key=GHOST_KEY)
    print("Ghost Admin API client succesvol geïnitialiseerd.")

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
        is_longread = 'longread' in filename.lower()
        
        base_tag = 'Long Read' if is_longread else 'Weekly Update'
        lang_code = filename.split('_')[-1].split('.')[0]
        lang_tag = lang_code.upper()
        final_tags = [base_tag, lang_tag]

        with open(filepath, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
            # Eerste regel als titel pakken en opschonen
            title = markdown_text.splitlines()[0].strip().replace('# ', '')
            
            # FIX: Verwijder de "Article Title:" prefix
            if title.lower().startswith('article title:'):
                title = title[len('article title:'):].strip()

        html_from_markdown = markdown.markdown(markdown_text)
        
        for attempt in range(MAX_RETRIES):
            try:
                print(f"Poging {attempt + 1}/{MAX_RETRIES}: Publiceren van '{title}'...")
                published_post = ghost.create_post(title=title, html_content=html_from_markdown, tags=final_tags)
                post_url = published_post.get('url')
                print(f"✅ SUCCES: Post '{published_post['title']}' is nu gepubliceerd op {post_url}")
                
                if is_longread and lang_code == 'en':
                    with open(URL_OUTPUT_FILE, "w", encoding="utf-8") as url_file:
                        url_file.write(post_url)
                    print(f"INFO: Long-read URL opgeslagen in {URL_OUTPUT_FILE}")

                break 
            except requests.exceptions.RequestException as e:
                print(f"!!! FOUT (Poging {attempt + 1}) bij API-aanroep: {e}", file=sys.stderr)
                if attempt + 1 == MAX_RETRIES:
                    print(f"!!! DEFINITIEVE FOUT: Kon '{title}' niet publiceren.", file=sys.stderr)
                else:
                    print(f"Wacht {RETRY_DELAY} seconden...")
                    time.sleep(RETRY_DELAY)
            except Exception as e:
                print(f"!!! ONVERWACHTE FOUT bij '{title}': {e}", file=sys.stderr)
                break