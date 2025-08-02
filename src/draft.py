# src/draft.py
import json
import os
import datetime
import sys
import argparse
import google.generativeai as genai
from openai import OpenAI

def eprint(*args, **kwargs):
    """Helper functie om naar stderr te printen."""
    print(*args, file=sys.stderr, **kwargs)

# --- AI Model Selectie ---
API_TYPE = os.getenv('AI_API_TYPE')
MODEL_ID = os.getenv('AI_MODEL_ID')
API_KEY = os.getenv('AI_API_KEY')
BASE_URL = os.getenv('AI_BASE_URL')

PROMPT_TPL_PATH = "prompts/step3.txt"
CURATED_DATA_PATH = "curated.json"
LANGUAGES_CONFIG_PATH = "languages.json"
OUTPUT_DIR = "content/posts"

model = None
eprint(f"Provider type: {API_TYPE}, Model: {MODEL_ID}")

if API_TYPE == 'google':
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_ID)
elif API_TYPE == 'openai_compatible':
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    class OpenRouterModel:
        def generate_content(self, prompt):
            response = client.chat.completions.create(model=MODEL_ID, messages=[{"role": "user", "content": prompt}])
            content = ""
            # FIX: 'choices' is een lijst. Pak het eerste element.
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if choice.message and choice.message.content:
                    content = choice.message.content

            class ResponseWrapper:
                def __init__(self, text): self.text = text
            return ResponseWrapper(content)
    model = OpenRouterModel()
else:
    raise ValueError(f"Ongeldig AI_API_TYPE: {API_TYPE}")

# --- Datum Logica ---
parser = argparse.ArgumentParser(description="Genereer een nieuwsbrief voor een specifieke datum in meerdere talen.")
parser.add_argument('--date', type=str, help="De datum voor de nieuwsbrief in YYYY-MM-DD formaat.")
args = parser.parse_args()

target_date = datetime.date.today()
if args.date:
    try:
        target_date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
    except ValueError:
        eprint(f"❌ Ongeldig datumformaat voor --date: '{args.date}'. Gebruik YYYY-MM-DD.")
        exit(1)

today_iso = target_date.isoformat()
eprint(f"Nieuwsbrieven worden geschreven voor datum: {today_iso}")

# --- Data en Talen Laden ---
with open(PROMPT_TPL_PATH, "r", encoding="utf-8") as f:
    PROMPT_TPL = f.read()
try:
    with open(CURATED_DATA_PATH, "r", encoding="utf-8") as f:
        news_data = json.load(f)
    with open(LANGUAGES_CONFIG_PATH, "r", encoding="utf-8") as f:
        all_languages = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    eprint(f"❌ Fout bij laden van configuratie- of databestanden. Fout: {e}")
    exit(1)

active_languages = [lang for lang in all_languages if lang.get("enabled", False)]

if not active_languages:
    eprint("⚠️ Geen talen ingeschakeld in 'languages.json'.")
    exit(0)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Hoofdlogica: Loop over actieve talen ---
successful_drafts = 0
for lang_config in active_languages:
    lang_code = lang_config['code']
    lang_name = lang_config['name']
    edition_word = lang_config['edition_word']
    
    eprint("-" * 30)
    eprint(f"Voorbereiden van nieuwsbrief voor taal: {lang_name} ({lang_code})")
    
    edition_date_str = target_date.strftime('%d %b %Y')
    
    prompt = PROMPT_TPL.replace('{json_data}', json.dumps(news_data, indent=2, ensure_ascii=False))
    prompt = prompt.replace('{lang}', lang_name)
    prompt = prompt.replace('{edition_word}', edition_word)
    prompt = prompt.replace('{edition_date}', edition_date_str)

    eprint(f"🤖 Model '{MODEL_ID}' wordt aangeroepen voor de {lang_name} nieuwsbrief...")
    try:
        response = model.generate_content(prompt)
        md = response.text
        if md.strip().startswith("```markdown"):
            md = md.strip()[10:-3].strip()
        elif md.strip().startswith("```"):
             md = md.strip()[3:-3].strip()
        
        raw_title = md.splitlines()[0].lstrip('# ').strip()
        safe_title = raw_title.replace('"', '”')
        
        article_date = target_date.isoformat()
        
        front_matter = f"""---
title: "{safe_title}"
date: {article_date}
---

"""
        
        full_content = front_matter + md
        
        output_filename = f"{OUTPUT_DIR}/{today_iso}_{lang_code}.md"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(full_content)
        eprint(f"✅ {output_filename} geschreven")
        successful_drafts += 1 # Tel een succesvolle poging op

    except Exception as e:
        eprint(f"❌ Fout bij API aanroep voor {lang_name}: {e}")
        continue # Ga door naar de volgende taal

# --- DE NIEUWE CONTROLE IS HIER ---
# Controleer na de loop of alle talen zijn verwerkt.
if successful_drafts < len(active_languages):
    eprint(f"❌ MISLUKT: Slechts {successful_drafts} van de {len(active_languages)} nieuwsbrieven konden worden gegenereerd.")
    sys.exit(1) # Sluit af met een foutcode

eprint("-" * 30)
eprint("✅ Alle ingeschakelde talen zijn verwerkt.")