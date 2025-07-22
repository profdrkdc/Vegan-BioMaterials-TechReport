# src/fetch.py
import json
import os
import datetime
import time
import google.generativeai as genai
from openai import OpenAI

PROMPT_FILE = "prompts/step1.txt"
OUTPUT_FILE = "raw.json"
MAX_RETRIES = 3
AI_PROVIDER = os.getenv('AI_PROVIDER', 'google')

model = None
model_id_for_log = ""
print(f"Gekozen AI Provider: {AI_PROVIDER}")

if AI_PROVIDER == 'google':
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY: raise ValueError("GOOGLE_API_KEY niet ingesteld.")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    model_id_for_log = 'gemini-1.5-flash-latest'

elif AI_PROVIDER in ['openrouter_kimi', 'openrouter_mistral']:
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    if not OPENROUTER_API_KEY: raise ValueError("OPENROUTER_API_KEY niet ingesteld.")
    
    model_id = "moonshotai/kimi-k2:free" if AI_PROVIDER == 'openrouter_kimi' else "mistralai/mistral-7b-instruct"
    model_id_for_log = model_id
    
    openrouter_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    
    class OpenRouterModel:
        def generate_content(self, prompt):
            response = openrouter_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
            )
            # --- FIX IS HIER ---
            # Correcte manier om de response te benaderen
            return type('obj', (object,), {'text': response.choices[0].message.content})()
    model = OpenRouterModel()
else:
    raise ValueError(f"Ongeldige AI_PROVIDER: {AI_PROVIDER}.")

with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_template = f.read()

today = datetime.date.today().isoformat()
prompt = prompt_template.replace('{today}', today)

print(f"🤖 Model '{model_id_for_log}' wordt aangeroepen...")
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
    except Exception as e:
        print(f"⚠️ Poging {attempt + 1}/{MAX_RETRIES} mislukt: {e}")
        if attempt + 1 == MAX_RETRIES:
            print("❌ Alle pogingen zijn mislukt. Script stopt.")
            print("--- Laatst ontvangen van AI ---\n" + raw_content)
            exit(1)
        time.sleep(5)