# src/fetch.py
import json
import os
import datetime
import time
import google.generativeai as genai
from openai import OpenAI

# --- Configuratie ---
PROMPT_FILE = "prompts/step1.txt"
OUTPUT_FILE = "raw.json"
MAX_RETRIES = 3
AI_PROVIDER = os.getenv('AI_PROVIDER', 'google') # Default naar google als niet ingesteld

# --- Model Initialisatie (Dynamisch) ---
model = None
print(f"Gekozen AI Provider: {AI_PROVIDER}")

if AI_PROVIDER == 'google':
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable not set for Google provider.")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
elif AI_PROVIDER == 'openrouter':
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set for OpenRouter provider.")
    openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    # Wrapper om de OpenAI client compatibel te maken met de .generate_content() methode
    class OpenRouterModel:
        def generate_content(self, prompt):
            response = openrouter_client.chat.completions.create(
                model="kimi-ml/kimi-2-128k",
                messages=[{"role": "user", "content": prompt}],
            )
            return type('obj', (object,), {'text': response.choices[0].message.content})()
    model = OpenRouterModel()
else:
    raise ValueError(f"Ongeldige AI_PROVIDER: {AI_PROVIDER}. Kies 'google' of 'openrouter'.")

# --- Hoofdlogica (ongewijzigd) ---
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_template = f.read()

today = datetime.date.today().isoformat()
prompt = prompt_template.replace('{today}', today)

print("🤖 Model wordt aangeroepen om de laatste data te verzamelen...")
raw_content = ""

for attempt in range(MAX_RETRIES):
    try:
        response = model.generate_content(prompt)
        raw_content = response.text
        
        if raw_content.strip().startswith("```json"):
            raw_content = raw_content.strip()[7:-3].strip()
            
        data = json.loads(raw_content)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Ruwe data succesvol verzameld en opgeslagen in {OUTPUT_FILE}.")
        break
        
    except (json.JSONDecodeError, IndexError, ValueError) as e:
        print(f"⚠️ Poging {attempt + 1}/{MAX_RETRIES} mislukt: {e}")
        if attempt + 1 == MAX_RETRIES:
            print("❌ Alle pogingen zijn mislukt. Script stopt.")
            print("--- Laatst ontvangen van AI ---\n" + raw_content)
            exit(1)
        time.sleep(5)