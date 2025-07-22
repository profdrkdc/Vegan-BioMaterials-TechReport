# src/generate_longread.py
import os
import argparse
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
# LangChain imports
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
# Dynamische model imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# --- Pydantic modellen (ongewijzigd) ---
class ArticleSection(BaseModel):
    # ...
class ArticleOutline(BaseModel):
    # ...

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
    
    print(f"Model geïnitialiseerd: {llm.model_name}")

    # --- Prompts en Ketens (logica is ongewijzigd, alleen llm is dynamisch) ---
    parser_outline = PydanticOutputParser(pydantic_object=ArticleOutline)
    prompt_outline = PromptTemplate(template="...", input_variables=["topic"], partial_variables={"format_instructions": parser_outline.get_format_instructions()})
    chain_outline = prompt_outline | llm | parser_outline
    print("✓ Chain 1 (Outline) has been built.")

    prompt_full_article = PromptTemplate.from_template("...")
    chain_full_article = prompt_full_article | llm | StrOutputParser()
    print("✓ Chain 2 (Full Article Writer) has been built.")
    

    # --- CHAIN 1: Outline Generation ---
    parser_outline = PydanticOutputParser(pydantic_object=ArticleOutline)
    prompt_outline = PromptTemplate(
        template="""
You are an expert content strategist specializing in deep-dive analyses of vegan biotech and food-tech.
Your task is to create a detailed, logically structured outline for an in-depth article (approx. 1500-2000 words) based on the provided topic.

Topic:
{topic}

The outline should guide the reader from a general overview to specific details and a future outlook.
Ensure a catchy title and a list of sections with specific, substantive talking points.

{format_instructions}
""",
        input_variables=["topic"],
        partial_variables={"format_instructions": parser_outline.get_format_instructions()},
    )
    chain_outline = prompt_outline | llm | parser_outline
    print("✓ Chain 1 (Outline) has been built.")

    # --- CHAIN 2: Section Writing (per section) ---
    prompt_section = PromptTemplate.from_template(
        """
You are a talented writer who can explain complex topics clearly and engagingly.
Write a detailed and well-supported section for a larger article, based on the following instructions.

Section Title: {title}
Key points to cover: {talking_points}

Write approximately 300-400 words. Maintain a smooth, informative, and professional style.
Write the output directly in Markdown. Do not use extra headers for the section itself, only the raw text.
---
SECTION CONTENT:"""
    )
    chain_section_writer = prompt_section | llm | StrOutputParser()
    print("✓ Chain 2 (Section Writer) has been built.")

    # --- CHAIN 3: Synthesis (combining into a final article) ---
    prompt_synthesis = PromptTemplate.from_template(
        """
You are the final editor. Your task is to merge the following individually written sections into a single, coherent, and publication-ready long-read article.

Article Title: {title}
Context for Introduction: {introduction_hook}
Context for Conclusion: {conclusion_summary}

Here are the fully written sections:
---
{sections_text}
---

Your tasks:
1.  Write a compelling, overarching introduction (approx. 150-200 words). Use the 'Context for Introduction' as inspiration.
2.  Seamlessly stitch the provided sections together. Ensure smooth transitions where necessary, but do not alter the core of the sections.
3.  Write a powerful conclusion (approx. 150-200 words) that summarizes the key points and offers a look to the future. Use the 'Context for Conclusion' as a basis.
4.  Format the entire final result as a single, coherent Markdown document. Start with the main title (H1: # Title). Use H2 (##) for section titles.

FINAL ARTICLE:
"""
    )
    chain_synthesis = prompt_synthesis | llm | StrOutputParser()
    print("✓ Chain 3 (Synthesis) is built.")
    print("-" * 50)


    # --- Execution (Step-by-step) ---
    print("Step 1: Generating outline...")
    outline = chain_outline.invoke({"topic": topic})
    print(f"✓ Outline received with {len(outline.sections)} sections.")
    print("-" * 50)

    print("Step 2: Writing sections (one by one)...")
    written_sections = []
    for i, section in enumerate(outline.sections):
        print(f"  -> Writing section {i+1}/{len(outline.sections)}: '{section.title}'")
        section_text = chain_section_writer.invoke(section.model_dump())
        written_sections.append(section_text)
        time.sleep(2)

    print("✓ All sections have been written.")
    print("-" * 50)

    print("Step 3: Final editing and synthesis...")
    sections_with_titles = []
    for i, section_text in enumerate(written_sections):
        section_title = outline.sections[i].title
        sections_with_titles.append(f"## {section_title}\n\n{section_text}")
    sections_text_combined = "\n\n".join(sections_with_titles)
    
    synthesis_input = {
        "title": outline.title,
        "introduction_hook": outline.introduction_hook,
        "conclusion_summary": outline.conclusion_summary,
        "sections_text": sections_text_combined,
    }

    final_article = chain_synthesis.invoke(synthesis_input)
    print("✓ Synthesis complete!")
    print("-" * 50)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_article)
    print(f"✅ Article successfully saved as: {output_path}")


# --- Main entry point of the script ---
if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate a long-read article on a specific topic using LangChain.")
    parser.add_argument("topic", type=str, help="The main topic of the article.")
    parser.add_argument("-o", "--output", type=str, default="longread_output.md", help="The path to the output Markdown file.")
    parser.add_argument("--api-key", type=str, help="Optional: Google AI API key. Overrides the environment variable.")
    args = parser.parse_args()

    if args.api_key:
        os.environ["GOOGLE_API_KEY"] = args.api_key
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: Google API Key not found.")
        print("Set the GOOGLE_API_KEY environment variable, or provide it with --api-key.")
        exit(1)

    generate_longread_article(args.topic, args.output)