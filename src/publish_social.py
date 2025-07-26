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
    """Publiceert een post op Reddit met verbeterde flair-logica."""
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
        
        text_content = post_content.get('text_content')
        title = reddit_details.get('post_title')
        
        # --- VERBETERDE FLAIR LOGICA ---
        suggested_flair_text = reddit_details.get('suggested_flair_text')
        flair_id = None
        
        if suggested_flair_text:
            eprint(f"INFO: Zoeken naar flair voor suggestie: '{suggested_flair_text}'...")
            try:
                available_flairs = list(subreddit.flair.link_templates)
                
                # DIAGNOSTISCH: Print de beschikbare flairs
                available_texts = [f"'{f['text']}'" for f in available_flairs]
                eprint(f"DEBUG: Beschikbare flairs op r/{target_subreddit}: {', '.join(available_texts)}")

                # 1. Zoek naar een exacte (case-insensitive) match
                for flair in available_flairs:
                    if flair['text'].lower() == suggested_flair_text.lower():
                        flair_id = flair['id']
                        eprint(f"INFO: Exacte flair match gevonden: '{flair['text']}'")
                        break
                
                # 2. Fallback: Als geen match, zoek naar generieke opties
                if not flair_id:
                    eprint("INFO: Geen exacte match. Zoeken naar fallback ('Article' of 'Discussion')...")
                    fallback_options = ['article', 'discussion']
                    for flair in available_flairs:
                        if flair['text'].lower() in fallback_options:
                            flair_id = flair['id']
                            eprint(f"INFO: Fallback flair match gevonden: '{flair['text']}'")
                            break

            except Exception as e:
                eprint(f"⚠️ WAARSCHUWING: Kon flairs niet ophalen of verwerken. Fout: {e}")
        # --- EINDE FLAIR LOGICA ---

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