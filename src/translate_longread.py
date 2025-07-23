# src/translate_longread.py
import os
import sys
import argparse
import google.generativeai as genai
from openai import OpenAI

def eprint(*args, **kwargs):
    """Helper functie om naar stderr te printen."""
    print(*args, file=sys.stderr, **kwargs)

def translate_article(source_path: str, output_path: str, lang_name: str):
    """Vertaalt een artikel met behoud van Markdown-opmaak."""
    
    API_TYPE = os.getenv('AI_API_TYPE')
    MODEL_ID = os.getenv('AI_MODEL_ID')
    API_KEY = os.getenv('AI_API_KEY')
    BASE_URL = os.getenv('AI_BASE_URL')
    
    model = None
    eprint(f"Provider type voor vertaling: {API_TYPE}, Model: {MODEL_ID}")

    if API_TYPE == 'google':
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_ID)
    elif API_TYPE == 'openai_compatible':
        client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
        class OpenRouterModel:
            def generate_content(self, prompt):
                response = client.chat.completions.create(model=MODEL_ID, messages=[{"role": "user", "content": prompt}])
                class ResponseWrapper:
                    def __init__(self, content): self.text = content
                return ResponseWrapper(response.choices[0].message.content)
        model = OpenRouterModel()
    else:
        raise ValueError(f"Ongeldig AI_API_TYPE: {API_TYPE}.")

    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            original_text = f.read()
    except FileNotFoundError:
        eprint(f"❌ Fout: Bronbestand niet gevonden op {source_path}", file=sys.stderr)
        exit(1)


    prompt = f"""
    You are a professional translator specializing in technical and journalistic content.
    Your task is to translate the following article from English to {lang_name}.

    **CRITICAL RULES:**
    1.  Translate the text accurately, maintaining the original tone and meaning.
    2.  Pay close attention to idioms and figurative language (e.g., "a foothold", "a double-edged sword"). Do NOT translate these literally. Find the equivalent idiomatic expression in {lang_name} or rephrase the concept naturally.
    3.  You MUST preserve ALL original Markdown formatting (e.g., `# `, `## `, `*`, `**`, `_`).
    4.  Do not add any commentary, notes, or introductions. Your output must be ONLY the translated article text.

    --- START OF ARTICLE TO TRANSLATE ---
    {original_text}
    --- END OF ARTICLE TO TRANSLATE ---
    """
    
    eprint(f"🤖 Model '{MODEL_ID}' wordt aangeroepen om artikel naar {lang_name} te vertalen met verbeterde prompt...")
    response = model.generate_content(prompt)
    translated_text = response.text

    if translated_text.strip().startswith("```markdown"):
        translated_text = translated_text.strip()[10:-3].strip()
    elif translated_text.strip().startswith("```"):
            translated_text = translated_text.strip()[3:-3].strip()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(translated_text)
    
    eprint(f"✅ Artikel succesvol vertaald en opgeslagen als: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vertaalt een long-read artikel naar een andere taal.")
    parser.add_argument("source", type=str, help="Het pad naar het Engelse bron .md-bestand.")
    parser.add_argument("output", type=str, help="Het pad voor het vertaalde output .md-bestand.")
    parser.add_argument("--lang_name", required=True, type=str, help="De volledige naam van de doeltaal (bv. 'Nederlands').")
    args = parser.parse_args()

    translate_article(args.source, args.output, args.lang_name)