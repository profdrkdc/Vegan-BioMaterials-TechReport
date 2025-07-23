# src/generate_longread.py
import os, sys, argparse
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class ArticleSection(BaseModel):
    title: str = Field(description="The title of this section of the article.")
    talking_points: List[str] = Field(description="A list of 3-5 key points to be covered in this section.")
    pass

class ArticleOutline(BaseModel):
    title: str = Field(description="A catchy, SEO-friendly title for the entire article.")
    introduction_hook: str = Field(description="A short sentence or a compelling idea to start the introduction.")
    sections: List[ArticleSection] = Field(description="The list of sections to be written for the article.")
    conclusion_summary: str = Field(description="A brief summary of the main idea for the conclusion.")
    pass

def generate_longread_article(topic: str, output_path: str):
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
        llm = ChatOpenAI(model_name=MODEL_ID, openai_api_base=BASE_URL, openai_api_key=API_KEY, temperature=0.7)
    else:
        raise ValueError(f"Ongeldig AI_API_TYPE: {API_TYPE}")
    
    eprint(f"LangChain model geïnitialiseerd: {llm.model_name}")

    parser_outline = PydanticOutputParser(pydantic_object=ArticleOutline)
    prompt_outline_text = """
    You are an expert content strategist specializing in deep-dive analyses of vegan biotech and food-tech.
    Your task is to create a detailed, logically structured outline for an in-depth article (approx. 1500-2000 words) based on the provided topic.
    Topic: {topic}
    The outline should guide the reader from a general overview to specific details and a future outlook.
    Ensure a catchy title and a list of sections with specific, substantive talking points.
    {format_instructions}
    """
    prompt_outline = PromptTemplate(template=prompt_outline_text, input_variables=["topic"], partial_variables={"format_instructions": parser_outline.get_format_instructions()})
    chain_outline = prompt_outline | llm | parser_outline
    eprint("✓ Chain 1 (Outline) has been built.")

    prompt_full_article_text = """
    You are a talented writer and final editor. Your task is to write a complete, in-depth, and publication-ready long-read article based on the provided structured outline.
    Here is the complete outline to follow:
    ---
    Article Title: {title}
    Introduction Hook: {introduction_hook}
    Conclusion Summary: {conclusion_summary}
    Sections to write:
    {sections_list}
    ---
    Your tasks:
    1. Write a compelling, overarching introduction (approx. 150-200 words) inspired by the 'Introduction Hook'.
    2. Write a detailed and engaging section for EACH item in the 'Sections to write' list. Use the section title and its talking points as a guide for the content of each section.
    3. Ensure smooth transitions between sections.
    4. Write a powerful conclusion (approx. 150-200 words) that summarizes the key points, based on the 'Conclusion Summary'.
    5. Format the entire final result as a single, coherent Markdown document. Start with the main title (H1: # Title). Use H2 (##) for section titles.
    FINAL ARTICLE:
    """
    prompt_full_article = PromptTemplate.from_template(prompt_full_article_text)
    chain_full_article = prompt_full_article | llm | StrOutputParser()
    eprint("✓ Chain 2 (Full Article Writer) has been built.")
    eprint("-" * 50)

    eprint("Step 1: Generating outline...")
    outline = chain_outline.invoke({"topic": topic})
    eprint(f"✓ Outline received with title: '{outline.title}'")
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
    
    final_article = chain_full_article.invoke(article_input)
    eprint("✓ Full article generated!")
    eprint("-" * 50)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_article)
    eprint(f"✅ Article successfully saved as: {output_path}")

# --- FIX IS HIER ---
if __name__ == "__main__":
    # Laad .env bestand voor lokale tests (optioneel)
    load_dotenv()
    
    # Zet de command-line parser op, net als in de andere scripts
    parser = argparse.ArgumentParser(description="Generate a long-read article on a specific topic using LangChain.")
    parser.add_argument("topic", type=str, help="The main topic of the article.")
    parser.add_argument("-o", "--output", type=str, default="longread_output.md", help="The path to the output Markdown file.")
    
    # Parse de argumenten
    args = parser.parse_args()
    
    # Roep de hoofdfunctie aan met de geparste argumenten
    generate_longread_article(args.topic, args.output)