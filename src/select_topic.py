# src/select_topic.py
import os, glob, argparse, sys
import google.generativeai as genai
from openai import OpenAI

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def get_latest_newsletter_file(content_dir="content"):
    search_path = os.path.join(content_dir, "*_en.md")
    files = glob.glob(search_path)
    if not files:
        raise FileNotFoundError(f"Geen Engelse nieuwsbrief (*_en.md) gevonden in '{content_dir}'.")
    return max(files)

def select_best_topic(newsletter_content: str) -> str:
    # Lees configuratie uit environment
    API_TYPE = os.getenv('AI_API_TYPE')
    MODEL_ID = os.getenv('AI_MODEL_ID')
    API_KEY = os.getenv('AI_API_KEY')
    BASE_URL = os.getenv('AI_BASE_URL')
    
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
        raise ValueError(f"Ongeldig AI_API_TYPE: {API_TYPE}.")

    prompt = f"""
    You are a senior content strategist for the "Vegan BioTech Report".
    Your task is to analyze the following weekly newsletter and identify the single most compelling topic for a deep-dive, long-read article (1500-2500 words).
    The ideal topic should have significant long-term impact, be based on a concrete news item, and be broad enough for a deep analysis.
    Analyze the newsletter content below:
    ---
    {newsletter_content}
    ---
    Based on your analysis, formulate a single, descriptive sentence that can be used as a direct input prompt for another AI writer.
    **CRITICAL:** Your ENTIRE output must be ONLY this single sentence. Do not add any commentary, headings, or quotation marks.
    """
    
    eprint(f"🤖 Model '{MODEL_ID}' wordt aangeroepen om onderwerp te selecteren...")
    response = model.generate_content(prompt)
    selected_topic = response.text.strip().strip('"')
    return selected_topic

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selecteert het beste long-read onderwerp uit de laatste nieuwsbrief.")
    parser.add_argument("--content_dir", type=str, default="content", help="De map waar de nieuwsbriefbestanden staan.")
    args = parser.parse_args()
    try:
        latest_newsletter = get_latest_newsletter_file(args.content_dir)
        eprint(f"Meest recente nieuwsbrief gevonden: {latest_newsletter}")
        with open(latest_newsletter, 'r', encoding='utf-8') as f:
            content = f.read()
        topic = select_best_topic(content)
        # De enige output naar stdout is de topic zelf
        print(topic)
    except Exception as e:
        eprint(f"❌ Fout: {e}")
        exit(1)