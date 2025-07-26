# src/publish_social.py
import os
import sys
import json
from dotenv import load_dotenv

def eprint(*args, **kwargs):
    """Helper functie om naar stderr te printen."""
    print(*args, file=sys.stderr, **kwargs)
    
# (De functie post_to_mastodon blijft ongewijzigd)
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

def find_flair_id(search_term, available_flairs, flair_type=""):
    """Hulpfunctie om een flair ID te vinden op basis van een zoekterm."""
    for flair in available_flairs:
        if flair['text'].lower() == search_term.lower():
            eprint(f"INFO ({flair_type}): Exacte flair match gevonden: '{flair['text']}'")
            return flair['id']
    for flair in available_flairs:
        if search_term.lower() in flair['text'].lower():
            eprint(f"INFO ({flair_type}): Gedeeltelijke flair match gevonden: '{flair['text']}'")
            return flair['id']
    return None
    
def post_to_reddit(post_content):
    """Publiceert een post op Reddit, inclusief abonneren op de subreddit."""
    reddit_details = post_content.get('reddit_details')
    if not reddit_details:
        eprint("❌ FOUT: Kan niet posten op Reddit. 'reddit_details' object ontbreekt.")
        return
        
    target_subreddit = reddit_details.get('suggested_subreddit', 'r/test').lstrip('r/')
    eprint(f"-> Poging tot publicatie op Reddit in r/{target_subreddit}...")

    try:
        import praw
        from praw.exceptions import RedditAPIException
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
        
        # --- NIEUWE LOGICA: Abonneer op subreddit als dat nog niet is gebeurd ---
        try:
            if not subreddit.user_is_subscriber:
                eprint(f"INFO: Account is nog geen lid van r/{target_subreddit}. Poging tot abonneren...")
                subreddit.subscribe()
                eprint(f"✅ SUCCES: Geabonneerd op r/{target_subreddit}.")
        except Exception as e:
            eprint(f"⚠️ WAARSCHUWING: Kon niet automatisch abonneren op subreddit. Fout: {e}")
        # --- EINDE NIEUWE LOGICA ---

        text_content = post_content.get('text_content')
        title = reddit_details.get('post_title')
        
        flair_id = None
        try:
            available_flairs = list(subreddit.flair.link_templates)
            preferred_keyword = "biotech"
            flair_id = find_flair_id(preferred_keyword, available_flairs, "P1 Preferred")

            if not flair_id:
                ai_keyword = reddit_details.get('primary_topic_keyword')
                if ai_keyword:
                    flair_id = find_flair_id(ai_keyword, available_flairs, "P2 AI")

            if not flair_id:
                fallback_keywords = ['discussion', 'article']
                for keyword in fallback_keywords:
                    flair_id = find_flair_id(keyword, available_flairs, "P3 Fallback")
                    if flair_id: break

        except Exception as e:
            eprint(f"⚠️ WAARSCHUWING: Kon flairs niet ophalen of verwerken. Fout: {e}")

        if not title:
            eprint("❌ FOUT: Kan niet posten op Reddit. 'post_title' ontbreekt.")
            return
        
        if not text_content:
            eprint("❌ FOUT: Kan niet posten op Reddit. 'text_content' is leeg.")
            return

        submission = subreddit.submit(title=title, selftext=text_content, flair_id=flair_id)
        eprint(f"✅ SUCCES: Gepost op Reddit! URL: {submission.shortlink}")

    except RedditAPIException as e:
        for subexception in e.items:
            if subexception.error_type == 'SUBMIT_VALIDATION_FLAIR_REQUIRED':
                eprint(f"❌ FOUT: r/{target_subreddit} vereist een flair, maar een geldige kon niet worden gevonden of ingesteld.")
                return
        eprint(f"❌ FOUT: Reddit API fout: {e}")
    except PrawcoreException as e:
        eprint(f"❌ FOUT: Kon niet verbinden met Reddit. Controleer je credentials. Foutmelding: {e}")
    except Exception as e:
        eprint(f"❌ FOUT: Een onverwachte fout is opgetreden bij Reddit: {e}")

if __name__ == "__main__":
    eprint("--- Starting Social Media Publisher ---")
    load_dotenv()
    
    URL_INPUT_FILE = "published_post_url.txt"
    try:
        with open(URL_INPUT_FILE, "r", encoding="utf-8") as f:
            article_url = f.read().strip()
        eprint(f"INFO: Specifieke artikel-URL geladen: {article_url}")
    except FileNotFoundError:
        eprint(f"⚠️ WAARSCHUWING: {URL_INPUT_FILE} niet gevonden. Fallback naar algemene GHOST_PUBLIC_URL.")
        article_url = os.getenv('GHOST_PUBLIC_URL')

    if not article_url:
        eprint("❌ FOUT: Geen artikel-URL of GHOST_PUBLIC_URL beschikbaar.")
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
            post['text_content'] = post['text_content'].replace('{{GHOST_ARTICLE_URL}}', article_url)

        if platform == "mastodon":
            post_to_mastodon(post)
        elif platform == "reddit":
            post_to_reddit(post)
        else:
            eprint(f"⚠️ WAARSCHUWING: Geen publicatielogica voor platform '{platform}'. Post wordt overgeslagen.")
            
    eprint("\n--- Social Media Publisher Finished ---")