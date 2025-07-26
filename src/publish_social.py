# src/publish_social.py
import os
import sys
import json
from dotenv import load_dotenv

def eprint(*args, **kwargs):
    """Helper functie om naar stderr te printen."""
    print(*args, file=sys.stderr, **kwargs)

def post_to_mastodon(post_content):
    """Publiceert een post op Mastodon."""
    eprint("-> Poging tot publicatie op Mastodon...")
    try:
        from mastodon import Mastodon, MastodonError
    except ImportError:
        eprint("❌ FOUT: De 'Mastodon.py' library is niet geïnstalleerd.")
        return

    api_base_url = os.getenv('MASTODON_API_BASE_URL')
    access_token = os.getenv('MASTODON_ACCESS_TOKEN')

    if not all([api_base_url, access_token]):
        eprint("❌ FOUT: Mastodon credentials niet gevonden in omgevingsvariabelen.")
        return

    try:
        mastodon_api = Mastodon(
            access_token=access_token,
            api_base_url=api_base_url
        )
        status = mastodon_api.status_post(post_content['text_content'])
        eprint(f"✅ SUCCES: Gepost op Mastodon! URL: {status['url']}")
    except MastodonError as e:
        eprint(f"❌ FOUT: Publicatie op Mastodon mislukt: {e}")
    except Exception as e:
        eprint(f"❌ FOUT: Een onverwachte fout is opgetreden bij Mastodon: {e}")

def post_to_reddit(post_content):
    """Publiceert een post op Reddit."""
    reddit_details = post_content.get('reddit_details')
    if not reddit_details:
        eprint("❌ FOUT: Kan niet posten op Reddit. 'reddit_details' object ontbreekt.")
        return
        
    target_subreddit = reddit_details.get('suggested_subreddit', 'r/test').lstrip('r/')
    eprint(f"-> Poging tot publicatie op Reddit in r/{target_subreddit}...")

    try:
        import praw
        from prawcore.exceptions import PrawcoreException
    except ImportError:
        eprint("❌ FOUT: De 'praw' library is niet geïnstalleerd.")
        return

    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    username = os.getenv('REDDIT_USERNAME')
    password = os.getenv('REDDIT_PASSWORD')
    user_agent = os.getenv('REDDIT_USER_AGENT')

    if not all([client_id, client_secret, username, password, user_agent]):
        eprint("❌ FOUT: Reddit credentials niet gevonden.")
        return

    try:
        reddit_api = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent
        )
        subreddit = reddit_api.subreddit(target_subreddit)
        
        text_content = post_content.get('text_content')
        title = reddit_details.get('post_title')

        if not title:
            eprint("❌ FOUT: Kan niet posten op Reddit. 'post_title' ontbreekt.")
            return
        
        if not text_content:
            eprint("❌ FOUT: Kan niet posten op Reddit. 'text_content' is leeg.")
            return

        submission = subreddit.submit(title=title, selftext=text_content)
        eprint(f"✅ SUCCES: Gepost op Reddit! URL: {submission.shortlink}")

    except PrawcoreException as e:
        eprint(f"❌ FOUT: Publicatie op Reddit mislukt: {e}")
    except Exception as e:
        eprint(f"❌ FOUT: Een onverwachte fout is opgetreden bij Reddit: {e}")

if __name__ == "__main__":
    eprint("--- Starting Social Media Publisher ---")
    load_dotenv()

    ghost_public_url = os.getenv('GHOST_PUBLIC_URL')
    if not ghost_public_url:
        eprint("❌ FOUT: GHOST_PUBLIC_URL niet gevonden in .env. Kan placeholder niet vervangen.")
        sys.exit(1)

    try:
        with open("social_posts.json", "r", encoding="utf-8") as f:
            posts_to_publish = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        eprint(f"❌ FOUT: Kan 'social_posts.json' niet lezen of parsen. Fout: {e}")
        sys.exit(1)

    for post in posts_to_publish:
        platform = post.get("platform")
        eprint(f"\nVerwerken van post voor platform: {platform}")
        
        if 'text_content' in post and post['text_content']:
            post['text_content'] = post['text_content'].replace('{{GHOST_POST_URL}}', ghost_public_url)

        if platform == "mastodon":
            post_to_mastodon(post)
        elif platform == "reddit":
            post_to_reddit(post)
        else:
            eprint(f"⚠️ WAARSCHUWING: Geen publicatielogica voor platform '{platform}'. Post wordt overgeslagen.")
            
    eprint("\n--- Social Media Publisher Finished ---")
    