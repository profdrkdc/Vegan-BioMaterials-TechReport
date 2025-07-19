# src/fetch.py

#!/usr/bin/env python3
"""
Fetch the latest vegan tech news from the AI model (Gemini).
Saves the raw output to raw.json.
Call: python -m src.fetch
"""
import json
import os
import datetime
import time
import google.generativeai as genai

# --- Configuratie ----------------------------------------------------
PROMPT_FILE = "prompts/step1.txt"
OUTPUT_FILE = "raw.json"
MAX_RETRIES = 3
# ---------------------------------------------------------------------

# --- Configuratie voor Gemini ---
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro') # <-- Aangepast naar 2.5 Pro
# ------------------------------------

# Lees de prompt template
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_template = f.read()

# Vul de datum van vandaag in
today = datetime.date.today().isoformat()
prompt = prompt_template.replace('{today}', today)

print("🤖 Gemini wordt aangeroepen om de laatste data te verzamelen...")
raw_content = "" # Initialiseer raw_content

# Loop voor meerdere pogingen
for attempt in range(MAX_RETRIES):
    try:
        response = model.generate_content(prompt)
        raw_content = response.text
        
        # Verwijder de ```json ... ``` markdown die Gemini soms toevoegt
        if raw_content.strip().startswith("```json"):
            raw_content = raw_content.strip()[7:-3].strip()
            
        data = json.loads(raw_content)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Ruwe data succesvol verzameld en opgeslagen in {OUTPUT_FILE}.")
        break
        
    except (json.JSONDecodeError, IndexError, ValueError) as e:
        print(f"⚠️ Poging {attempt + 1} van de {MAX_RETRIES} mislukt: Kon AI-respons niet parsen. Fout: {e}")
        if attempt + 1 == MAX_RETRIES:
            print("❌ Alle pogingen zijn mislukt. Het script stopt.")
            print("--- Laatst ontvangen van AI ---")
            print(raw_content)
            print("------------------------")
            exit(1)
        time.sleep(5)