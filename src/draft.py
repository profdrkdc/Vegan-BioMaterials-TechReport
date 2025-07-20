#!/usr/bin/env python3
"""
Generate bilingual newsletter from curated.json (using Gemini).
Call: python -m src.draft
"""
import json
import os
import datetime
import time
import google.generativeai as genai

# --- config ----------------------------------------------------------
LANGS = {"nl": "Nederlands", "en": "English"}
PROMPT_TPL_PATH = "prompts/step3.txt"
CURATED_DATA_PATH = "curated.json"
OUTPUT_DIR = "content"
# ---------------------------------------------------------------------

# --- Configuratie voor Gemini ---
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro')
# ------------------------------------

# Lees de prompt template
with open(PROMPT_TPL_PATH, "r", encoding="utf-8") as f:
    PROMPT_TPL = f.read()

# Laad de gecureerde data
try:
    with open(CURATED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"❌ Fout bij het laden van {CURATED_DATA_PATH}. Draai eerst fetch.py en curate.py. Fout: {e}")
    exit(1)

today = datetime.date.today()
today_iso = today.isoformat()

# Zorg ervoor dat de output-directory bestaat.
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Genereer de nieuwsbrief voor elke taal
for code, lang in LANGS.items():
    edition_word = "Editie" if lang == "Nederlands" else "Edition"
    edition_date = today.strftime('%d %b %Y') # e.g., 19 Jul 2025

    # Gebruik .replace() om alleen de placeholders te vervangen die we kennen.
    # Dit laat de placeholders voor de AI (zoals {company}) intact.
    prompt = PROMPT_TPL
    prompt = prompt.replace('{json_data}', json.dumps(data, indent=2, ensure_ascii=False))
    prompt = prompt.replace('{lang}', lang)
    prompt = prompt.replace('{edition_word}', edition_word)
    prompt = prompt.replace('{edition_date}', edition_date)

    print(f"🤖 Gemini wordt aangeroepen voor de {lang} nieuwsbrief...")

    try:
        response = model.generate_content(prompt)
        md = response.text

        # Schoon de output op (soms voegt de AI markdown-codeblokken toe)
        if md.strip().startswith("```markdown"):
            md = md.strip()[10:-3].strip()
        elif md.strip().startswith("```"):
             md = md.strip()[3:-3].strip()


        output_filename = f"{OUTPUT_DIR}/{today_iso}_{code}.md"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"✅ {output_filename} geschreven")

    except Exception as e:
        print(f"❌ Fout tijdens het aanroepen van de Gemini API voor {lang}: {e}")

    # Wacht 10 seconden tussen aanroepen om rate-limiting te voorkomen
    if code != list(LANGS.keys())[-1]:
        time.sleep(10)