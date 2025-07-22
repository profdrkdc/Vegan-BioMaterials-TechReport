# src/select_topic.py

import os
import glob
import argparse
import google.generativeai as genai

def get_latest_newsletter_file(content_dir="content"):
    """Zoekt en retourneert het pad naar het meest recente Engelse nieuwsbriefbestand."""
    search_path = os.path.join(content_dir, "*_en.md")
    files = glob.glob(search_path)
    if not files:
        raise FileNotFoundError(f"Geen Engelse nieuwsbriefbestanden (*_en.md) gevonden in de map '{content_dir}'.")
    # Sorteer de bestanden en pak de meest recente
    latest_file = max(files)
    return latest_file

def select_best_topic(newsletter_content: str) -> str:
    """
    Gebruikt de AI om het beste long-read onderwerp uit de nieuwsbrief te selecteren.
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    
    genai.configure(api_key=api_key)
    # We gebruiken het 'flash' model voor snelheid en om quota te respecteren.
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    prompt = f"""
    You are a senior content strategist for the "Vegan BioTech Report".
    Your task is to analyze the following weekly newsletter and identify the single most compelling topic for a deep-dive, long-read article (1500-2500 words).

    The ideal topic should:
    - Have significant long-term impact on the industry.
    - Be based on a concrete news item (like a major investment, a technological breakthrough, or a significant partnership).
    - Be broad enough for a deep analysis but specific enough to be focused.

    Analyze the newsletter content below:
    ---
    {newsletter_content}
    ---

    Based on your analysis, formulate a single, descriptive sentence that can be used as a direct input prompt for another AI writer to generate the long-read article.

    **CRITICAL:** Your ENTIRE output must be ONLY this single sentence. Do not add any commentary, headings, or quotation marks.
    For example, a good output would be:
    The recent $100M funding for 'AlgaeInnovate' and its implications for scaling up algae-based bioplastics as a viable alternative to petroleum products.
    """

    print("🤖 AI wordt aangeroepen om het beste long-read onderwerp te selecteren...")
    response = model.generate_content(prompt)
    
    # We strippen eventuele extra witruimte of aanhalingstekens
    selected_topic = response.text.strip().strip('"')
    
    return selected_topic

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selecteert het beste long-read onderwerp uit de laatste nieuwsbrief.")
    parser.add_argument(
        "--content_dir", 
        type=str, 
        default="content", 
        help="De map waar de nieuwsbriefbestanden staan."
    )
    args = parser.parse_args()

    try:
        latest_newsletter = get_latest_newsletter_file(args.content_dir)
        print(f"Meest recente nieuwsbrief gevonden: {latest_newsletter}")
        
        with open(latest_newsletter, 'r', encoding='utf-8') as f:
            content = f.read()
            
        topic = select_best_topic(content)
        
        # De output van dit script is ENKEL de topic-string.
        # Dit is essentieel zodat we het direct kunnen gebruiken in een workflow.
        print(topic)

    except FileNotFoundError as e:
        print(f"❌ Fout: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Een onverwachte fout is opgetreden: {e}")
        exit(1)