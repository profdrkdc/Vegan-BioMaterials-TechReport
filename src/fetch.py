#!/usr/bin/env python3
"""
Fetch the latest vegan tech news from the AI model.
Saves the raw output to raw.json.
Call: python -m src.fetch
"""
import json
import os
from openai import OpenAI

# --- Configuratie ----------------------------------------------------
# Zorg ervoor dat u een bestand 'prompts/step1.txt' heeft
# met daarin de data-verzamelingsprompt.
PROMPT_FILE = "prompts/step1.txt"
OUTPUT_FILE = "raw.json"
# ---------------------------------------------------------------------

# Initialiseer de client (identiek aan draft.py)
client = OpenAI(
    base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("KIMI_API_KEY")
)
model = "moonshotai/kimi-k2:free"

# Lees de prompt
try:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt = f.read()
except FileNotFoundError:
    print(f"❌ Fout: Het prompt-bestand {PROMPT_FILE} niet gevonden.")
    exit(1)

# Roep de API aan
print("🤖 AI wordt aangeroepen om de laatste data te verzamelen...")
res = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}]
)

# Verwerk de respons
# De AI geeft een string terug die JSON bevat, dus we moeten deze parsen.
try:
    raw_content = res.choices[0].message.content
    data = json.loads(raw_content)
except (json.JSONDecodeError, IndexError) as e:
    print(f"❌ Fout: Kon de AI-respons niet parsen als JSON. Fout: {e}")
    print("--- Ontvangen van AI ---")
    print(raw_content)
    print("------------------------")
    exit(1)

# Sla de data op
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Ruwe data succesvol verzameld en opgeslagen in {OUTPUT_FILE}.")