# src/generate_longread.py
import os, sys, argparse, json, re, datetime
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class ArticleSection(BaseModel):
    title: str = Field(description="The title of this section of the article.")
    talking_points: List[str] = Field(description="A list of 3-5 key points to be covered in this section.")

class ArticleOutline(BaseModel):
    title: str = Field(description="A catchy, SEO-friendly title for the entire article.")
    introduction_hook: str = Field(description="A short sentence or a compelling idea to start the introduction.")
    sections: List[ArticleSection] = Field(description="The list of sections to be written for the article.")
    conclusion_summary: str = Field(description="A brief summary of the main idea for the conclusion.")

def generate_longread_article(outline_path: str, output_path: str, lang_name: str):
    eprint(f"AI pipeline started for language: {lang_name}...")
    API_TYPE = os.getenv('AI_API_TYPE')
    MODEL_ID = os.getenv('AI_MODEL_ID')
    API_KEY = os.getenv('AI_API_KEY')
    BASE_URL = os.getenv('AI_BASE_URL')
    llm = None
    
    eprint(f"Provider type: {API_TYPE}, Model: {MODEL_ID}")

    if API_TYPE == 'google':
        llm = ChatGoogleGenerativeAI(model=MODEL_ID, google_api_key=API_KEY, temperature=0.7)
    elif API_TYPE == 'openai_compatible':
        llm = ChatOpenAI(model=MODEL_ID, openai_api_base=BASE_URL, api_key=API_KEY, temperature=0.7)
    else:
        raise ValueError(f"Ongeldig AI_API_TYPE: {API_TYPE}")

    eprint(f"LangChain model geïnitialiseerd: {getattr(llm, 'model', 'Onbekend')}")

    try:
        with open(outline_path, "r", encoding="utf-8") as f:
            outline = ArticleOutline.model_validate_json(f.read())
        eprint(f"✓ Outline successfully loaded. English Title: '{outline.title}'")
    except FileNotFoundError:
        eprint(f"❌ Fout: Outline bestand niet gevonden op {outline_path}")
        sys.exit(1)

    eprint(f"Generating full article in {lang_name} from outline...")
    sections_list_str = ""
    for i, section in enumerate(outline.sections):
        sections_list_str += f"{i+1}. Title: {section.title}\n   Talking Points: {', '.join(section.talking_points)}\n"

    article_input = {
        "title": outline.title,
        "introduction_hook": outline.introduction_hook,
        "conclusion_summary": outline.conclusion_summary,
        "sections_list": sections_list_str,
        "lang_name": lang_name
    }
    
    prompt_full_article_text = """
    You are a talented writer. Your task is to write a complete, in-depth article in {lang_name} based on the provided structured English outline.

    CRITICAL: The ENTIRE article, including the title, must be written in {lang_name}.

    English Outline:
    - Article Title: {title}
    - Introduction Hook: {introduction_hook}
    - Conclusion Summary: {conclusion_summary}
    - Sections to write:
    {sections_list}

    Your tasks:
    1.  Create a new, catchy, and natural-sounding title for the article in {lang_name}. Do NOT literally translate the English title.
    2.  Write a compelling introduction in {lang_name} based on the 'Introduction Hook'.
    3.  Write a detailed section in {lang_name} for EACH item in the 'Sections to write' list.
    4.  Format the entire result as a single Markdown document. Start with the new # Title in {lang_name}. Use ## for section titles.

    FINAL ARTICLE IN {lang_name}:
    """
    prompt_full_article = PromptTemplate.from_template(prompt_full_article_text)
    chain_full_article = prompt_full_article | llm | StrOutputParser()
    eprint("✓ Full Article Writer Chain has been built.")
    
    final_article_markdown = chain_full_article.invoke(article_input)
    eprint(f"✓ Full article in {lang_name} generated!")
    eprint("-" * 50)
    
    # --- DE ROBUUSTE OPSCHOONLOGICA ---
    content = final_article_markdown
    if content.strip().startswith("```markdown"):
        content = content.strip()[10:]
    if content.strip().startswith("```"):
        content = content.strip()[3:]
    if content.strip().endswith("```"):
        content = content.strip()[:-3]
    content = content.strip()
    heading_pos = content.find('# ')
    if heading_pos > 0:
        content = content[heading_pos:]
    cleaned_markdown = content
    
    # Pak de titel uit de opgeschoonde content
    lines = cleaned_markdown.splitlines()
    safe_title = "Untitled"
    if lines and lines.startswith('# '):
        safe_title = lines.lstrip('# ').strip().replace('"', '”')

    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', output_path)
    article_date = date_match.group(1) if date_match else datetime.date.today().isoformat()

    front_matter = f"""---
title: "{safe_title}"
date: {article_date}
---

"""
    
    full_content = front_matter + cleaned_markdown
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_content)
    eprint(f"✅ Article with front matter successfully saved as: {output_path}")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate a long-read article from an outline in a specific language.")
    parser.add_argument("--outline-in", type=str, required=True, help="The path to the input JSON outline.")
    parser.add_argument("-o", "--output", type=str, required=True, help="The path to the output Markdown file.")
    parser.add_argument("--lang-name", required=True, type=str, help="The full name of the target language (e.g., 'Nederlands').")
    
    args = parser.parse_args()
    
    generate_longread_article(args.outline_in, args.output, args.lang_name)