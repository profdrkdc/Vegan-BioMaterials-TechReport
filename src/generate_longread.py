# src/generate_longread.py
import os
import argparse
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# --- Pydantic modellen ---
class ArticleSection(BaseModel):
    title: str = Field(description="The title of this section of the article.")
    talking_points: List[str] = Field(description="A list of 3-5 key points to be covered in this section.")
    # --- SYNTAX FIX ---
    pass

class ArticleOutline(BaseModel):
    title: str = Field(description="A catchy, SEO-friendly title for the entire article.")
    introduction_hook: str = Field(description="A short sentence or a compelling idea to start the introduction.")
    sections: List[ArticleSection] = Field(description="The list of sections to be written for the article.")
    conclusion_summary: str = Field(description="A brief summary of the main idea for the conclusion.")
    # --- SYNTAX FIX ---
    pass

def generate_longread_article(topic: str, output_path: str):
    print("AI pipeline started (efficient 2-step mode)...")
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'google')
    llm = None
    print(f"Gekozen AI Provider: {AI_PROVIDER}")

    if AI_PROVIDER == 'google':
        if not os.getenv('GOOGLE_API_KEY'): raise ValueError("GOOGLE_API_KEY niet ingesteld.")
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.7)
    elif AI_PROVIDER in ['openrouter_kimi', 'openrouter_mistral']:
        if not os.getenv('OPENROUTER_API_KEY'): raise ValueError("OPENROUTER_API_KEY niet ingesteld.")
        model_id = "moonshotai/kimi-k2:free" if AI_PROVIDER == 'openrouter_kimi' else "mistralai/mistral-7b-instruct"
        llm = ChatOpenAI(
            model_name=model_id,
            openai_api_key=os.getenv('OPENROUTER_API_KEY'),
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7
        )
    else:
        raise ValueError(f"Ongeldige AI_PROVIDER: {AI_PROVIDER}.")
    
    print(f"LangChain model geïnitialiseerd: {llm.model_name}")

    # --- KETEN 1: Outline Generation ---
    parser_outline = PydanticOutputParser(pydantic_object=ArticleOutline)
    prompt_outline_text = """
    You are an expert content strategist... (de rest van je prompt)
    Topic: {topic}
    {format_instructions}
    """
    prompt_outline = PromptTemplate(template=prompt_outline_text, input_variables=["topic"], partial_variables={"format_instructions": parser_outline.get_format_instructions()})
    chain_outline = prompt_outline | llm | parser_outline
    print("✓ Chain 1 (Outline) has been built.")

    # --- KETEN 2: Full Article Generation ---
    prompt_full_article_text = """
    You are a talented writer and final editor... (de rest van je prompt)
    Article Title: {title}
    ...
    Sections to write:
    {sections_list}
    ---
    FINAL ARTICLE:
    """
    prompt_full_article = PromptTemplate.from_template(prompt_full_article_text)
    chain_full_article = prompt_full_article | llm | StrOutputParser()
    print("✓ Chain 2 (Full Article Writer) has been built.")
    print("-" * 50)

    # --- Uitvoering (in 2 stappen) ---
    print("Step 1: Generating outline...")
    outline = chain_outline.invoke({"topic": topic})
    print(f"✓ Outline received with title: '{outline.title}'")
    print("-" * 50)

    print("Step 2: Generating full article from outline...")
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
    print("✓ Full article generated!")
    print("-" * 50)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_article)
    print(f"✅ Article successfully saved as: {output_path}")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate a long-read article on a specific topic using LangChain.")
    parser.add_argument("topic", type=str, help="The main topic of the article.")
    parser.add_argument("-o", "--output", type=str, default="longread_output.md", help="The path to the output Markdown file.")
    parser.add_argument("--api-key", type=str, help="Optional: API key. Overrides the environment variable.")
    args = parser.parse_args()

    # Deze logica is nu overbodig omdat de functie het zelf regelt.
    # We kunnen dit simpeler houden.
    generate_longread_article(args.topic, args.output)