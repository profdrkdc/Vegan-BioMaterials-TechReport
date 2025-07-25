#!/usr/bin/env python3
"""
Een standalone script om de API-verbindingen met Mastodon en Reddit te testen.

Dit script laadt credentials uit het .env-bestand en probeert een
eenvoudige, niet-destructieve actie uit te voeren (gebruikersinfo ophalen)
om te valideren of de API-sleutels correct zijn.

Gebruik:
1. Zorg dat je een .env bestand hebt met de social media sleutels.
2. Voer uit vanuit de terminal: python3 test_social_api.py
"""
import os
import sys
from dotenv import load_dotenv

def test_mastodon_connection():
    """Test de verbinding met de Mastodon API."""
    print("\n--- Testen van Mastodon API ---")
    
    try:
        from mastodon import Mastodon, MastodonError
    except ImportError:
        print("⚠️ WAARSCHUWING: De 'Mastodon.py' library is niet geïnstalleerd.")
        print("Installeer deze met: python3 -m pip install Mastodon.py")
        return

    api_base_url = os.getenv('MASTODON_API_BASE_URL')
    access_token = os.getenv('MASTODON_ACCESS_TOKEN')

    if not api_base_url or 'VUL_HIER' in api_base_url or not access_token or 'VUL_HIER' in access_token:
        print("⚠️ WAARSCHUWING: MASTODON_API_BASE_URL of MASTODON_ACCESS_TOKEN niet (correct) ingevuld in .env. Test overgeslagen.")
        return

    try:
        print(f"Verbinden met Mastodon instance: {api_base_url}...")
        api = Mastodon(
            access_token=access_token,
            api_base_url=api_base_url
        )
        account_info = api.account_verify_credentials()
        username = account_info['username']
        print(f"✅ SUCCES: Verbinding met Mastodon gelukt. Ingelogd als: {username}")
    except MastodonError as e:
        print(f"❌ FOUT: Kon niet verbinden met Mastodon. Foutmelding van API: {e}")
    except Exception as e:
        print(f"❌ FOUT: Een onverwachte fout is opgetreden: {e}")


def test_reddit_connection():
    """Test de verbinding met de Reddit API."""
    print("\n--- Testen van Reddit API ---")

    try:
        import praw
        from prawcore.exceptions import PrawcoreException
    except ImportError:
        print("⚠️ WAARSCHUWING: De 'praw' library is niet geïnstalleerd.")
        print("Installeer deze met: python3 -m pip install praw")
        return

    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    username = os.getenv('REDDIT_USERNAME')
    password = os.getenv('REDDIT_PASSWORD')
    user_agent = os.getenv('REDDIT_USER_AGENT')

    if not all([client_id, client_secret, username, password, user_agent]) or any('VUL_HIER' in (s or '') for s in [client_id, client_secret, username, password, user_agent]):
        print("⚠️ WAARSCHUWING: Een of meer Reddit-variabelen niet (correct) ingevuld in .env. Test overgeslagen.")
        return

    try:
        print("Verbinden met Reddit API...")
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent
        )
        user_info = reddit.user.me()
        if user_info:
            print(f"✅ SUCCES: Verbinding met Reddit gelukt. Ingelogd als: /u/{user_info.name}")
        else:
            print("❌ FOUT: Verbinding met Reddit lijkt gelukt, maar kon gebruikersinformatie niet ophalen.")
    except PrawcoreException as e:
        print(f"❌ FOUT: Kon niet verbinden met Reddit. Controleer je credentials. Foutmelding: {e}")
    except Exception as e:
        print(f"❌ FOUT: Een onverwachte fout is opgetreden: {e}")

if __name__ == "__main__":
    print("API Verbindingstester wordt gestart...")
    if not load_dotenv():
        print("LET OP: Geen .env bestand gevonden. Script vertrouwt op reeds ingestelde omgevingsvariabelen.", file=sys.stderr)
    
    test_mastodon_connection()
    test_reddit_connection()
    
    print("\n--- Alle tests voltooid ---")