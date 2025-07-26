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

    # --- NIEUWE, GETEMPLATISEERDE PROMPT ---
    prompt_outline_text = """
    You are an expert content strategist. Your task is to generate the content for a structured article outline based on the topic below.

    Topic: {topic}

    Please provide the content for the following fields. Use a unique separator `|||` between each field's content.

    1.  **title**: A catchy, SEO-friendly title for the entire article.
    2.  **introduction_hook**: A short sentence or a compelling idea to start the introduction.
    3.  **conclusion_summary**: A brief summary of the main idea for the conclusion.
    4.  **sections_data**: A list of 3-5 sections. For each section, provide a title and 3-5 comma-separated talking points. Format it as: `Section Title 1: point a, point b, point c|Section Title 2: point d, point e, point f`

    Your response should be a single line of text with the four pieces of content separated by `|||`.
    Example format: My Article Title|||This is the hook.|||This is the conclusion.|||Section 1: tp1, tp2|Section 2: tp3, tp4
    """
    prompt_outline = PromptTemplate(template=prompt_outline_text, input_variables=["topic"])
    
    chain = prompt_outline | llm | StrOutputParser()
    eprint("✓ Chain 1 (Outline Content Generator) has been built.")
    eprint("Step 1: Generating outline content...")

    response_text = chain.invoke({"topic": topic})
    
    # --- NIEUWE, HANDMATIGE PARSING EN JSON-CONSTRUCTIE ---
    eprint("INFO: Parsing response and constructing JSON object...")
    try:
        parts = response_text.split('|||')
        if len(parts) != 4:
            raise ValueError(f"Expected 4 parts separated by '|||', but got {len(parts)}.")
            
        title, intro_hook, conclusion_summ, sections_data_str = parts
        
        sections = []
        section_parts = sections_data_str.strip().split('|')
        for sec_part in section_parts:
            title_points_split = sec_part.split(':', 1)
            if len(title_points_split) != 2:
                eprint(f"Skipping malformed section: {sec_part}")
                continue
                
            sec_title = title_points_split.strip()
            talking_points = [p.strip() for p in title_points_split.split(',')]
            sections.append({"title": sec_title, "talking_points": talking_points})

        outline_dict = {
            "title": title.strip(),
            "introduction_hook": intro_hook.strip(),
            "sections": sections,
            "conclusion_summary": conclusion_summ.strip()
        }
        
        outline = ArticleOutline.model_validate(outline_dict)
        eprint(f"✓ Outline successfully constructed and validated. Title: '{outline.title}'")

    except Exception as e:
        eprint(f"--- Fout bij parsen van AI respons ---")
        eprint(f"Fout: {e}")
        eprint(f"Ontvangen tekst: {response_text}")
        raise

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
    