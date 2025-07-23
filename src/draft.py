# src/draft.py
import json
import os
import datetime
import time
import sys
import argparse # <-- Belangrijke import
import google.generativeai as genai
from openai import OpenAI

def eprint(*args, **kwargs):
    """Helper functie om naar stderr te printen."""
    print(*args, file=sys.stderr, **kwargs)

# Lees configuratie uit environment
API_TYPE = os.getenv('AI_API_TYPE')
MODEL_ID = os.getenv('AI_MODEL_ID')
API_KEY = os.getenv('AI_API_KEY')
BASE_URL = os.getenv('AI_BASE_URL')

LANGS = {"en": "English"}
PROMPT_TPL_PATH = "prompts/step3.txt"
CURATED_DATA_PATH = "curated.json"
OUTPUT_DIR = "content"

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
            class ResponseWrapper:
                def __init__(self, content): self.text = content
            return ResponseWrapper(response.choices[0].message.content)
    model = OpenRouterModel()
else:
    raise ValueError(f"Ongeldig AI_API_TYPE: {API_TYPE}")

# --- NIEUWE LOGICA VOOR DATUM ---
# Parse de command-line argumenten
parser = argparse.ArgumentParser(description="Genereer een nieuwsbrief voor een specifieke datum.")
parser.add_argument('--date', type=str, help="De datum voor de nieuwsbrief in YYYY-MM-DD formaat.")
args = parser.parse_args()

# Bepaal de te gebruiken datum
if args.date:
    try:
        target_date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
    except ValueError:
        eprint(f"❌ Ongeldig datumformaat voor --date: '{args.date}'. Gebruik YYYY-MM-DD.")
        exit(1)
else:
    target_date = datetime.date.today()

today_iso = target_date.isoformat()
eprint(f"Nieuwsbrief wordt geschreven voor datum: {today_iso}")
# --- EINDE NIEUWE LOGICA ---

with open(PROMPT_TPL_PATH, "r", encoding="utf-8") as f:
    PROMPT_TPL = f.read()
try:
    with open(CURATED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    eprint(f"❌ Fout bij laden {CURATED_DATA_PATH}. Fout: {e}")
    exit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

for code, lang in LANGS.items():
    edition_word = "Edition"
    # Gebruik de 'target_date' variabele
    edition_date = target_date.strftime('%d %b %Y')
    
    prompt = PROMPT_TPL.replace('{json_data}', json.dumps(data, indent=2, ensure_ascii=False))
    prompt = prompt.replace('{lang}', lang)
    prompt = prompt.replace('{edition_word}', edition_word)
    prompt = prompt.replace('{edition_date}', edition_date)

    eprint(f"🤖 Model '{MODEL_ID}' wordt aangeroepen voor de {lang} nieuwsbrief...")
    try:
        response = model.generate_content(prompt)
        md = response.text
        if md.strip().startswith("```markdown"):
            md = md.strip()[10:-3].strip()
        elif md.strip().startswith("```"):
             md = md.strip()[3:-3].strip()
        
        # Gebruik de 'today_iso' variabele die is afgeleid van 'target_date'
        output_filename = f"{OUTPUT_DIR}/{today_iso}_{code}.md"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(md)
        eprint(f"✅ {output_filename} geschreven")
    except Exception as e:
        eprint(f"❌ Fout bij API aanroep voor {lang}: {e}")
        raise e