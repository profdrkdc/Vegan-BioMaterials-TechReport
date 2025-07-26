# src/generate_longread.py
import os, sys, argparse, json, re
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from openai import OpenAI

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

def parse_outline_from_text(text: str) -> ArticleOutline:
    """Parses a structured text block into an ArticleOutline object."""
    eprint("INFO: Parsing response with new Markdown-based parser...")
    try:
        # Split de hoofdblokken
        parts = re.split(r'\[(TITLE|HOOK|CONCLUSION|SECTIONS)\]', text)
        
        content_map = {
            "TITLE": parts[2].strip() if len(parts) > 2 else "",
            "HOOK": parts[4].strip() if len(parts) > 4 else "",
            "CONCLUSION": parts[6].strip() if len(parts) > 6 else "",
            "SECTIONS": parts[8].strip() if len(parts) > 8 else ""
        }

        # Parse het SECTIONS blok
        parsed_sections = []
        current_section = None
        for line in content_map["SECTIONS"].splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("# "):
                if current_section:
                    parsed_sections.append(current_section)
                current_section = {"title": line.lstrip("# ").strip(), "talking_points": []}
            elif line.startswith("- ") and current_section:
                current_section["talking_points"].append(line.lstrip("- ").strip())
        
        if current_section:
            parsed_sections.append(current_section)

        outline_dict = {
            "title": content_map["TITLE"],
            "introduction_hook": content_map["HOOK"],
            "conclusion_summary": content_map["CONCLUSION"],
            "sections": parsed_sections
        }
        
        return ArticleOutline.model_validate(outline_dict)

    except Exception as e:
        eprint(f"--- Fout bij parsen van AI respons ---")
        eprint(f"Fout: {e}")
        eprint(f"Ontvangen tekst:\n{text}")
        raise

def generate_longread_article(topic: str, output_path: str, outline_output_path: str):
    eprint("AI pipeline started (efficient 2-step mode)...")
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

    # --- NIEUWE, ROBUUSTERE PROMPT ---
    prompt_outline_text = """
    You are an expert content strategist. Your task is to generate a structured article outline based on the topic below.

    Topic: {topic}

    Please provide the content using the following Markdown format. Separate each block with its tag.

    [TITLE]
    A catchy, SEO-friendly title for the entire article.

    [HOOK]
    A short sentence or a compelling idea for the introduction.

    [CONCLUSION]
    A brief summary of the main idea for the conclusion.

    [SECTIONS]
    # Section 1: A descriptive title for the first section
    - Talking point 1 for section 1
    - Talking point 2 for section 1
    - Talking point 3 for section 1
    # Section 2: A descriptive title for the second section
    - Talking point 1 for section 2
    - Talking point 2 for section 2
    # ... continue for 3 to 5 sections in total
    """
    prompt_outline = PromptTemplate(template=prompt_outline_text, input_variables=["topic"])
    
    chain = prompt_outline | llm | StrOutputParser()
    eprint("✓ Chain 1 (Outline Content Generator) has been built.")
    eprint("Step 1: Generating outline content...")

    response_text = chain.invoke({"topic": topic})
    
    outline = parse_outline_from_text(response_text)
    eprint(f"✓ Outline successfully constructed and validated. Title: '{outline.title}'")

    with open(outline_output_path, "w", encoding="utf-8") as f:
        f.write(outline.model_dump_json(indent=2))
    eprint(f"✅ Outline successfully saved as: {outline_output_path}")
    eprint("-" * 50)

    eprint("Step 2: Generating full article from outline...")
    sections_list_str = ""
    for i, section in enumerate(outline.sections):
        sections_list_str += f"{i+1}. Title: {section.title}\n   Talking Points: {', '.join(section.talking_points)}\n"

    article_input = {
        "title": outline.title,
        "introduction_hook": outline.introduction_hook,
        "conclusion_summary": outline.conclusion_summary,
        "sections_list": sections_list_str
    }
    
    prompt_full_article_text = """
    You are a talented writer. Your task is to write a complete, in-depth article based on the provided structured outline.
    Here is the complete outline to follow:
    ---
    Article Title: {title}
    Introduction Hook: {introduction_hook}
    Conclusion Summary: {conclusion_summary}
    Sections to write:
    {sections_list}
    ---
    Your tasks:
    1. Write a compelling introduction based on the 'Introduction Hook'.
    2. Write a detailed section for EACH item in the 'Sections to write' list.
    3. Ensure smooth transitions between sections.
    4. Write a powerful conclusion based on the 'Conclusion Summary'.
    5. Format the entire result as a single Markdown document. Start with # Title. Use ## for section titles.
    FINAL ARTICLE:
    """
    prompt_full_article = PromptTemplate.from_template(prompt_full_article_text)
    chain_full_article = prompt_full_article | llm | StrOutputParser()
    eprint("✓ Chain 2 (Full Article Writer) has been built.")
    
    final_article = chain_full_article.invoke(article_input)
    eprint("✓ Full article generated!")
    eprint("-" * 50)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_article)
    eprint(f"✅ Article successfully saved as: {output_path}")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate a long-read article on a specific topic using LangChain.")
    parser.add_argument("topic", type=str, help="The main topic of the article.")
    parser.add_argument("-o", "--output", type=str, default="longread_output.md", help="The path to the output Markdown file.")
    parser.add_argument("--outline-out", type=str, default="longread_outline.json", help="The path to save the JSON outline.")
    args = parser.parse_args()
    generate_longread_article(args.topic, args.output, args.outline_out)