# src/draft.py
import json, os, datetime, time, google.generativeai as genai
from openai import OpenAI

# --- FIX: Alleen Engels ---
LANGS = {"en": "English"}
PROMPT_TPL_PATH = "prompts/step3.txt"
CURATED_DATA_PATH = "curated.json"
OUTPUT_DIR = "content"
AI_PROVIDER = os.getenv('AI_PROVIDER', 'google')
model, model_id_for_log = None, ""

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
            response = openrouter_client.chat.completions.create(model=model_id, messages=[{"role": "user", "content": prompt}])
            return type('SimpleResponse', (object,), {'text': response.choices.message.content})()
    model = OpenRouterModel()
else:
    raise ValueError(f"Ongeldige AI_PROVIDER: {AI_PROVIDER}.")

with open(PROMPT_TPL_PATH, "r", encoding="utf-8") as f:
    PROMPT_TPL = f.read()
try:
    with open(CURATED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"❌ Fout bij laden {CURATED_DATA_PATH}. Fout: {e}")
    exit(1)

today = datetime.date.today()
today_iso = today.isoformat()
os.makedirs(OUTPUT_DIR, exist_ok=True)

for code, lang in LANGS.items():
    edition_word = "Edition"
    edition_date = today.strftime('%d %b %Y')
    prompt = PROMPT_TPL.replace('{json_data}', json.dumps(data, indent=2, ensure_ascii=False))
    prompt = prompt.replace('{lang}', lang)
    prompt = prompt.replace('{edition_word}', edition_word)
    prompt = prompt.replace('{edition_date}', edition_date)

    print(f"🤖 Model '{model_id_for_log}' wordt aangeroepen voor de {lang} nieuwsbrief...")
    try:
        response = model.generate_content(prompt)
        md = response.text
        if md.strip().startswith("```markdown"):
            md = md.strip()[10:-3].strip()
        elif md.strip().startswith("```"):
             md = md.strip()[3:-3].strip()
        output_filename = f"{OUTPUT_DIR}/{today_iso}_{code}.md"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ {output_filename} geschreven")
    except Exception as e:
        print(f"❌ Fout bij API aanroep voor {lang}: {e}")

    # --- FIX IS HIER ---
    # Voeg een pauze toe om rate-limiting te voorkomen
    if code != list(LANGS.keys())[-1]:
        print("--- Pauze van 15 seconden om rate-limit te respecteren ---")
        time.sleep(15)