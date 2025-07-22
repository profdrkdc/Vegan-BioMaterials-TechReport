# src/select_topic.py
# (vervang de functie select_best_topic)
def select_best_topic(newsletter_content: str) -> str:
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'google')
    model = None
    model_id_for_log = ""
    print(f"Gekozen AI Provider voor topic selectie: {AI_PROVIDER}")

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
                return type('obj', (object,), {'text': response.choices.message.content})()
        model = OpenRouterModel()
    else:
        raise ValueError(f"Ongeldige AI_PROVIDER: {AI_PROVIDER}.")


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

    print("🤖 AI wordt aangeroepen om het beste long-read onderwerp te selecteren...")
    response = model.generate_content(prompt)
    selected_topic = response.text.strip().strip('"')
    return selected_topic

# --- Hoofdingang (ongewijzigd) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selecteert het beste long-read onderwerp uit de laatste nieuwsbrief.")
    parser.add_argument("--content_dir", type=str, default="content", help="De map waar de nieuwsbriefbestanden staan.")
    args = parser.parse_args()
    try:
        latest_newsletter = get_latest_newsletter_file(args.content_dir)
        print(f"Meest recente nieuwsbrief gevonden: {latest_newsletter}")
        with open(latest_newsletter, 'r', encoding='utf-8') as f:
            content = f.read()
        topic = select_best_topic(content)
        print(topic)
    except Exception as e:
        print(f"❌ Fout: {e}")
        exit(1)