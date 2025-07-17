#!/usr/bin/env python3
"""
Generate bilingual newsletter from curated.json
Call: python -m src.draft
"""
import json, os, datetime
from openai import OpenAI

# --- config ----------------------------------------------------------
LANGS = {"nl": "Nederlands", "en": "English"}
PROMPT_TPL = open("prompts/step3.txt", encoding="utf-8").read()
# ---------------------------------------------------------------------

client = OpenAI(
    base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("KIMI_API_KEY")
)
model = "moonshotai/kimi-k2:free"

data = json.load(open("curated.json", encoding="utf-8"))
today = datetime.date.today().isoformat()

for code, lang in LANGS.items():
    prompt = PROMPT_TPL.format(json_data=json.dumps(data, indent=2), lang=lang)
    res = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
    md = res.choices[0].message.content
    open(f"content/{today}_{code}.md", "w", encoding="utf-8").write(md)
    print(f"✅ {today}_{code}.md written")