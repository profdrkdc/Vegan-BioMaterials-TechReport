#!/usr/bin/env python3
"""
Fetch the latest vegan tech news from the AI model.
Saves the raw output to raw.json.
Call: python -m src.fetch
"""
import json
import os
import datetime
import time # VOEG TOE
from openai import OpenAI

# --- Configuratie ----------------------------------------------------
PROMPT_FILE = "prompts/step1.txt"
OUTPUT_FILE = "raw.json"
MAX_RETRIES = 3 # Aantal nieuwe pogingen
# ---------------------------------------------------------------------

client = OpenAI(
    base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("KIMI_API_KEY")
)
model = "moonshotai/kimi-k2:free"

# Lees de prompt template
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_template = f.read()

# Vul de datum van vandaag in
today = datetime.date.today().isoformat()
prompt = prompt_template.replace('{today}', today)

print("🤖 AI wordt aangeroepen om de laatste data te verzamelen...")

# Loop voor meerdere pogingen
for attempt in range(MAX_RETRIES):
    try:
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_content = res.choices[0].message.content
        data = json.loads(raw_content) # Probeer de JSON te parsen

        # Als het succesvol is, schrijf de data weg en stop de loop
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Ruwe data succesvol verzameld en opgeslagen in {OUTPUT_FILE}.")
        break # Verlaat de loop na succes

    except (json.JSONDecodeError, IndexError) as e:
        print(f"⚠️ Poging {attempt + 1} van de {MAX_RETRIES} mislukt: Kon AI-respons niet parsen als JSON. Fout: {e}")
        if attempt + 1 == MAX_RETRIES:
            print("❌ Alle pogingen zijn mislukt. Het script stopt.")
            print("--- Laatst ontvangen van AI ---")
            print(raw_content)
            print("------------------------")
            exit(1) # Stop het script met een foutcode
        time.sleep(5) # Wacht 5 seconden voor de volgende poging