# src/generate_social_posts.py

#!/usr/bin/env python3
"""
Generates social media posts based on the week's curated news and long-read article outline.
"""
import os
import sys
import json
import re
import argparse
import google.generativeai as genai
from openai import OpenAI

def eprint(*args, **kwargs):
    """Helper function to print to stderr."""
    print(*args, file=sys.stderr, **kwargs)

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Generate social media posts from weekly content.")
    parser.add_argument('--dry-run', action='store_true', help="Run without calling the AI API, using fake data instead.")
    args = parser.parse_args()

    eprint("--- Start: Social Media Post Generation (Efficient Mode) ---")
    if args.dry_run:
        eprint("💧 DRY RUN MODE: AI API calls will be skipped.")

    try:
        with open("prompts/step4_social.txt", "r", encoding="utf-8") as f:
            prompt_tpl = f.read()
        with open("curated.json", "r", encoding="utf-8") as f:
            curated_data = json.load(f)
        outline_path = "longread_outline.json"
        with open(outline_path, "r", encoding="utf-8") as f:
            longread_outline = json.load(f)
        eprint(f"Context Long-Read Outline: {outline_path}")
    except FileNotFoundError as e:
        eprint(f"❌ Fout bij laden van input bestanden: {e}")
        sys.exit(1)
    
    raw_content = ""
    if args.dry_run:
        eprint("💧 Gebruik van vooraf gedefinieerde nep-data als AI-respons.")
        with open("social_posts.json", "r", encoding="utf-8") as f:
             raw_content = f.read()
    else:
        API_TYPE = os.getenv('AI_API_TYPE')
        MODEL_ID = os.getenv('AI_MODEL_ID')
        API_KEY = os.getenv('AI_API_KEY')
        BASE_URL = os.getenv('AI_BASE_URL')
        
        if not all([API_TYPE, MODEL_ID, API_KEY]):
            eprint("❌ AI-configuratie ontbreekt in omgevingsvariabelen.")
            sys.exit(1)

        model = None
        eprint(f"Provider type: {API_TYPE}, Model: {MODEL_ID}")

        if API_TYPE == 'google':
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel(MODEL_ID)
        elif API_TYPE == 'openai_compatible':
            client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
            class OpenRouterModel:
                def generate_content(self, prompt):
                    response = client.chat.completions.create(model=MODEL_ID, messages=[{"role": "user", "content": prompt}])
                    content = ""
                    if response.choices and response.choices:
                        if response.choices.message:
                            content = response.choices.message.content
                        elif hasattr(response.choices, 'text'):
                            content = response.choices.text
                    class ResponseWrapper:
                        def __init__(self, text): self.text = text
                    return ResponseWrapper(content)
            model = OpenRouterModel()
        else:
            eprint(f"❌ Ongeldig AI_API_TYPE: {API_TYPE}")
            sys.exit(1)

        top_news = curated_data[:3]
        top_news_json = json.dumps(top_news, indent=2, ensure_ascii=False)
        longread_outline_json = json.dumps(longread_outline, indent=2, ensure_ascii=False)
        prompt = prompt_tpl.replace('{top_news_json}', top_news_json)
        prompt = prompt.replace('{longread_outline_json}', longread_outline_json)
        
        eprint(f"🤖 Model '{MODEL_ID}' wordt aangeroepen voor social media content...")
        try:
            response = model.generate_content(prompt)
            raw_content = response.text
        except Exception as e:
            eprint(f"❌ Fout tijdens API aanroep: {e}")
            sys.exit(1)

    try:
        eprint("INFO: Cleaning AI response from potential hallucinated tags...")
        cleaned_content = re.sub(r'<[^>]+>', '', raw_content)
        
        json_match = re.search(r'\[.*\]', cleaned_content, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
            social_posts = json.loads(json_string)
        else:
            raise ValueError("Geen valide JSON array gevonden in de AI-respons.")

        with open("social_posts.json", "w", encoding="utf-8") as f:
            json.dump(social_posts, f, indent=2, ensure_ascii=False)
        
        eprint(f"✅ Social media posts succesvol verwerkt en opgeslagen in social_posts.json.")

    except Exception as e:
        eprint(f"❌ Fout tijdens verwerken van de respons: {e}")
        eprint(f"--- Ontvangen content voor verwerking (na schoonmaak) ---\n{cleaned_content}")
        sys.exit(1)

    eprint("--- Einde: Social Media Post Generation ---")

if __name__ == "__main__":
    main()
    