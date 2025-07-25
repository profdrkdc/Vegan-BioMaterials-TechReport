# src/generate_social_posts.py

#!/usr/bin/env python3
"""
Generates social media posts based on the week's curated news and long-read article.
- Reads curated.json and the latest English long-read.
- Calls an AI model to generate post variations.
- Saves the result to social_posts.json.
Call: python3 -m src.generate_social_posts
"""
import os
import sys
import json
import glob
import re
import argparse
import google.generativeai as genai
from openai import OpenAI

def eprint(*args, **kwargs):
    """Helper function to print to stderr."""
    print(*args, file=sys.stderr, **kwargs)

# --- FAKE AI RESPONSE FOR DRY RUN ---
FAKE_AI_RESPONSE = """
[
  {
    "platform": "x_twitter",
    "text_content": "This week in the Vegan BioTech Report: The future of eco-friendly materials and major breakthroughs in precision fermentation. Read the full analysis now! #foodtech #biotech #sustainability",
    "link_to_share": "{{GHOST_POST_URL}}",
    "image_prompt": null,
    "reddit_details": null
  },
  {
    "platform": "instagram",
    "text_content": "Is this the end of traditional leather? Our latest deep-dive explores the new generation of mycelium-based materials that are revolutionizing fashion and design. Link in bio for the full story!\\n\\n#veganleather #mycelium #biomaterials #sustainablefashion #biotech",
    "link_to_share": "{{GHOST_POST_URL}}",
    "image_prompt": "A hyper-realistic, luxurious handbag that seamlessly transitions from mushroom gills on one side to high-fashion vegan leather on the other, displayed in a minimalist boutique setting, soft lighting.",
    "reddit_details": null
  },
  {
    "platform": "reddit",
    "text_content": "Our new long-read investigates how precision fermentation is moving beyond food additives to create bulk proteins, potentially disrupting the entire dairy and egg industry within a decade.",
    "link_to_share": "{{GHOST_POST_URL}}",
    "image_prompt": null,
    "reddit_details": {
      "suggested_subreddit": "r/futurology",
      "post_title": "A deep-dive into how precision fermentation is now creating bulk proteins, challenging the economic viability of traditional animal agriculture."
    }
  }
]
"""
# --- END FAKE RESPONSE ---


def find_latest_longread(directory: str) -> str or None:
    """Finds the most recent English long-read file based on filename date."""
    search_path = os.path.join(directory, "longread_*_en.md")
    files = glob.glob(search_path)
    if not files:
        return None
    return max(files, key=os.path.getctime)

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Generate social media posts from weekly content.")
    parser.add_argument('--dry-run', action='store_true', help="Run without calling the AI API, using fake data instead.")
    args = parser.parse_args()

    eprint("--- Start: Social Media Post Generation ---")
    if args.dry_run:
        eprint("💧 DRY RUN MODE: AI API calls will be skipped.")

    # --- Load Input Data ---
    try:
        with open("prompts/step4_social.txt", "r", encoding="utf-8") as f:
            prompt_tpl = f.read()
        
        with open("curated.json", "r", encoding="utf-8") as f:
            curated_data = json.load(f)
        
        latest_longread_path = find_latest_longread("content")
        if not latest_longread_path:
            eprint(f"❌ Geen Engels long-read bestand gevonden in 'content'. Kan niet doorgaan.")
            sys.exit(1)
        
        eprint(f"Context Long-Read: {latest_longread_path}")
        with open(latest_longread_path, "r", encoding="utf-8") as f:
            longread_content = f.read()

    except FileNotFoundError as e:
        eprint(f"❌ Fout bij laden van input bestanden: {e}")
        eprint("Zorg ervoor dat 'curated.json' en een 'content/longread_..._en.md' bestand bestaan voor de test.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        eprint(f"❌ Fout bij parsen van curated.json: {e}")
        sys.exit(1)
    
    raw_content = ""
    if args.dry_run:
        eprint("💧 Gebruik van vooraf gedefinieerde nep-data als AI-respons.")
        raw_content = FAKE_AI_RESPONSE
    else:
        # --- AI Model Initialization (only if not a dry run) ---
        API_TYPE = os.getenv('AI_API_TYPE')
        MODEL_ID = os.getenv('AI_MODEL_ID')
        API_KEY = os.getenv('AI_API_KEY')
        BASE_URL = os.getenv('AI_BASE_URL')
        
        if not all([API_TYPE, MODEL_ID, API_KEY]):
            eprint("❌ AI-configuratie (API_TYPE, MODEL_ID, API_KEY) ontbreekt in omgevingsvariabelen.")
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
                    class ResponseWrapper:
                        def __init__(self, content): self.text = content
                    return ResponseWrapper(response.choices[0].message.content)
            model = OpenRouterModel()
        else:
            eprint(f"❌ Ongeldig AI_API_TYPE: {API_TYPE}")
            sys.exit(1)

        # --- Prepare and Call AI Model ---
        top_news = curated_data[:3]
        top_news_json = json.dumps(top_news, indent=2, ensure_ascii=False)
        prompt = prompt_tpl.replace('{top_news_json}', top_news_json)
        prompt = prompt.replace('{longread_content}', longread_content)
        
        eprint(f"🤖 Model '{MODEL_ID}' wordt aangeroepen voor social media content...")
        try:
            response = model.generate_content(prompt)
            raw_content = response.text
        except Exception as e:
            eprint(f"❌ Fout tijdens API aanroep: {e}")
            sys.exit(1)

    # --- Process Response (for both dry run and real run) ---
    try:
        json_match = re.search(r'\[.*\]', raw_content, re.DOTALL)
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
        eprint("--- Ontvangen content voor verwerking ---")
        eprint(raw_content)
        sys.exit(1)

    eprint("--- Einde: Social Media Post Generation ---")

if __name__ == "__main__":
    main()