#!/usr/bin/env python3
"""
Generate bilingual newsletter from curated.json
Call: python -m src.draft
"""
import json, os, datetime, time
from openai import OpenAI

# --- config ----------------------------------------------------------
LANGS = {"nl": "Nederlands", "en": "English"}
PROMPT_TPL = open("prompts/step3.txt", encoding="utf-8").read()
# ---------------------------------------------------------------------

# Initialiseer de client
client = OpenAI(
    base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("KIMI_API_KEY")
)
model = "moonshotai/kimi-k2:free"

# Laad de gecureerde data
data = json.load(open("curated.json", encoding="utf-8"))
today = datetime.date.today().isoformat()

# Zorg ervoor dat de output-directory bestaat.
# Dit voorkomt een FileNotFoundError in schone omgevingen zoals GitHub Actions.
os.makedirs("content", exist_ok=True)
# ---------------------------------

# Genereer de nieuwsbrief voor elke taal
for code, lang in LANGS.items():
    # Kies het juiste woord voor de editie op basis van de taal
    if lang == "Nederlands":
        edition_word = "Editie"
    else:
        edition_word = "Edition"

    # Begin met de onbewerkte template
    prompt = PROMPT_TPL

    # Vervang alle placeholders die Python moet invullen
    prompt = prompt.replace('{json_data}', json.dumps(data, indent=2))
    prompt = prompt.replace('{lang}', lang)
    prompt = prompt.replace('{today}', today)
    prompt = prompt.replace('{edition_word}', edition_word)

    # Roep de AI aan
    res = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
    md = res.choices[0].message.content

    # Schrijf het resultaat naar een .md-bestand
    open(f"content/{today}_{code}.md", "w", encoding="utf-8").write(md)
    print(f"✅ {today}_{code}.md written")

    # Wacht 10 seconden om rate-limiting te voorkomen
    time.sleep(10)