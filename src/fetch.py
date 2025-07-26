# src/fetch.py
import json
import os
import datetime
import time
import re
import sys
import argparse
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

PROMPT_FILE = "prompts/step1.txt"
OUTPUT_FILE = "raw.json"
MAX_RETRIES = 3

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
parser = argparse.ArgumentParser(description="Verzamel nieuws voor een specifieke datum.")
parser.add_argument('--date', type=str, help="De datum voor de nieuws-zoekopdracht in YYYY-MM-DD formaat.")
args = parser.parse_args()

run_date_iso = datetime.date.today().isoformat()
if args.date:
    try:
        datetime.datetime.strptime(args.date, '%Y-%m-%d')
        run_date_iso = args.date
    except ValueError:
        eprint(f"❌ Ongeldig datumformaat voor --date: '{args.date}'. Gebruik YYYY-MM-DD.")
        exit(1)

eprint(f"Data wordt verzameld met als referentiedatum: {run_date_iso}")

# --- Hoofdlogica ---
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_template = f.read()

prompt = prompt_template.replace('{today}', run_date_iso)

eprint(f"🤖 Model '{MODEL_ID}' wordt aangeroepen...")
raw_content = ""
for attempt in range(MAX_RETRIES):
    try:
        response = model.generate_content(prompt)
        raw_content = response.text
        
        json_match = re.search(r'\[.*\]', raw_content, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
            data = json.loads(json_string)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            eprint(f"✅ Ruwe data succesvol verzameld en opgeslagen in {OUTPUT_FILE}.")
            break
        else:
            raise ValueError("Geen valide JSON array gevonden in de AI-respons.")

    except Exception as e:
        eprint(f"⚠️ Poging {attempt + 1}/{MAX_RETRIES} mislukt: {e}")
        if attempt + 1 == MAX_RETRIES:
            eprint("❌ Alle pogingen zijn mislukt. Script stopt.")
            eprint(f"--- Laatst ontvangen van AI ---\n{raw_content}")
            exit(1)
        time.sleep(5)