# src/publish_linkedin.py
import os
import glob
import json
import sys
import re
import requests
import markdown
import google.generativeai as genai
from openai import OpenAI

def eprint(*args, **kwargs):
    """Helper functie om naar stderr te printen."""
    print(*args, file=sys.stderr, **kwargs)

def slugify(text):
    """Converteert een string naar een URL-vriendelijke slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def get_ai_model():
    """Initialiseert en retourneert het AI-model op basis van omgevingsvariabelen."""
    API_TYPE = os.getenv('AI_API_TYPE', 'google') # Standaard op google
    MODEL_ID = os.getenv('AI_MODEL_ID')
    API_KEY = os.getenv('AI_API_KEY')
    BASE_URL = os.getenv('AI_BASE_URL')

    if not all([MODEL_ID, API_KEY]):
        eprint("❌ AI-configuratie (MODEL_ID, API_KEY) is onvolledig. Kan geen samenvattingen genereren.")
        return None

    eprint(f"🤖 Initialiseren van AI-model. Provider: {API_TYPE}, Model: {MODEL_ID}")

    if API_TYPE == 'google':
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel(MODEL_ID)
    elif API_TYPE == 'openai_compatible':
        client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
        class OpenRouterModel:
            def generate_content(self, prompt):
                response = client.chat.completions.create(model=MODEL_ID, messages=[{"role": "user", "content": prompt}])
                class ResponseWrapper:
                    def __init__(self, content): self.text = content
                return ResponseWrapper(response.choices[0].message.content)
        return OpenRouterModel()
    else:
        eprint(f"❌ Ongeldig AI_API_TYPE: {API_TYPE}")
        return None

def generate_linkedin_summary(model, content, title, lang_code):
    """Genereert een korte, pakkende LinkedIn post met behulp van een AI-model."""
    eprint(f"Een LinkedIn-samenvatting genereren voor '{title}'...")
    html = markdown.markdown(content)
    plain_text = re.sub('<[^<]+?>', '', html)
    max_input_length = 8000
    if len(plain_text) > max_input_length:
        plain_text = plain_text[:max_input_length] + "..."

    prompt = f"""
    Je bent een social media expert gespecialiseerd in LinkedIn voor een tech-publicatie genaamd "Vegan BioTech Report".
    Je taak is om een korte, pakkende en professionele LinkedIn post te schrijven op basis van het onderstaande artikel.

    Richtlijnen:
    - De toon moet informatief en professioneel zijn, en de lezer nieuwsgierig maken.
    - Gebruik 2-4 relevante hashtags zoals #BioTech, #Duurzaamheid, #Innovatie, #FoodTech, #Vegan.
    - De post moet eindigen met een call-to-action die de lezer aanmoedigt om het volledige artikel te lezen.
    - De totale post (exclusief de link) mag niet langer zijn dan ~250 woorden.
    - Schrijf de post in de taal van het artikel (taalcode: {lang_code}).
    - BELANGRIJK: De output moet ALLEEN de tekst van de LinkedIn post zijn. Geen extra commentaar.

    Artikel content:
    ---
    Titel: {title}
    Tekst:
    {plain_text}
    ---
    Genereer nu de LinkedIn post.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        eprint(f"⚠️ Fout bij het genereren van LinkedIn samenvatting: {e}")
        fallback_summary = " ".join(plain_text.split('.')[:2]) + "."
        return f"{title}\n\n{fallback_summary}"

def post_to_linkedin(access_token, author_urn, post_text, article_url, title):
    """Plaatst een artikel op LinkedIn."""
    api_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    post_body = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "ARTICLE",
                "media": [{"status": "READY", "originalUrl": article_url, "title": {"text": title}}]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    eprint(f"Posten naar LinkedIn: '{title}'")
    response = requests.post(api_url, headers=headers, data=json.dumps(post_body))
    if response.status_code == 201:
        eprint("✅ Succesvol gepost op LinkedIn!")
    else:
        eprint(f"❌ Fout bij het posten op LinkedIn. Status: {response.status_code}, Response: {response.text}")
        response.raise_for_status()

if __name__ == "__main__":
    try:
        # Essentiële secrets laden
        LINKEDIN_TOKEN = os.environ['LINKEDIN_ACCESS_TOKEN']
        GHOST_URL = os.environ['GHOST_ADMIN_API_URL'].split('/ghost')[0]

        # Verbeterde URN-afhandeling: gebruik organisatie-URN als die er is, anders persoon-URN.
        LINKEDIN_ORG_URN = os.environ.get('LINKEDIN_ORGANIZATION_URN')
        LINKEDIN_PERSON_URN = os.environ.get('LINKEDIN_PERSON_URN')
        LINKEDIN_AUTHOR_URN = LINKEDIN_ORG_URN or LINKEDIN_PERSON_URN

        if not LINKEDIN_AUTHOR_URN:
            eprint("❌ Fout: Je moet ofwel LINKEDIN_ORGANIZATION_URN of LINKEDIN_PERSON_URN instellen in je GitHub secrets.")
            sys.exit(1)
    except KeyError as e:
        eprint(f"❌ Fout: De omgevingsvariabele {e} is niet ingesteld. Kan niet posten op LinkedIn.")
        sys.exit(1)

    ai_model = get_ai_model()
    if not ai_model:
        eprint("Stoppen omdat er geen AI-model beschikbaar is voor het maken van samenvattingen.")
        sys.exit(1)

    CONTENT_DIR = "content"
    files_to_publish = glob.glob(os.path.join(CONTENT_DIR, "*.md"))
    if not files_to_publish:
        eprint("Geen .md bestanden gevonden om te publiceren op LinkedIn.")
        sys.exit(0)

    for filepath in files_to_publish:
        eprint(f"\n--- Verwerken van bestand voor LinkedIn: {filepath} ---")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            title = content.splitlines()[0].strip().replace('# ', '')
            lang_code = os.path.basename(filepath).split('_')[-1].split('.')[0]
            article_url = f"{GHOST_URL}/{slugify(title)}/"
            linkedin_text = generate_linkedin_summary(ai_model, content, title, lang_code)
            
            post_to_linkedin(LINKEDIN_TOKEN, LINKEDIN_AUTHOR_URN, linkedin_text, article_url, title)
        except Exception as e:
            eprint(f"!!! Fout bij het verwerken van bestand '{filepath}': {e}")
            continue