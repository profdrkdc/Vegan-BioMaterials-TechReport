
import os
import google.auth
from googleapiclient.discovery import build

def get_blogger_service():
    """Initialiseert de Blogger API-service met credentials die automatisch worden opgehaald."""
    credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/blogger'])
    service = build('blogger', 'v3', credentials=credentials)
    return service

def create_post(title, content, is_draft=False):
    """Maakt een nieuwe post op Blogger."""
    blog_id = os.getenv('BLOGGER_BLOG_ID')
    if not blog_id:
        raise ValueError("BLOGGER_BLOG_ID omgevingsvariabele niet ingesteld.")

    service = get_blogger_service()
    body = {
        'title': title,
        'content': content
    }
    posts = service.posts()
    request = posts.insert(blogId=blog_id, body=body, isDraft=is_draft)
    try:
        post = request.execute()
        print(f"Post '{post['title']}' succesvol gepubliceerd op URL: {post['url']}")
        return post
    except Exception as e:
        print(f"Fout bij het publiceren naar Blogger: {e}")
        raise

if __name__ == '__main__':
    # Voorbeeld van direct gebruik (vereist ingestelde omgevingsvariabelen)
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and os.getenv('BLOGGER_BLOG_ID'):
        test_title = "Test Post via Script"
        test_content = "<p>Dit is een testbericht, automatisch gegenereerd.</p>"
        create_post(test_title, test_content)
    else:
        print("Stel GOOGLE_APPLICATION_CREDENTIALS en BLOGGER_BLOG_ID in om te testen.")
