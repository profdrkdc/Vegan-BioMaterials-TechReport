# src/generate_longread_outline.py
import os, sys, argparse, json, re
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from src.generate_longread import parse_outline_from_text, ArticleOutline

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def generate_outline(topic: str, outline_output_path: str):
    eprint("AI pipeline started (outline generation only)...")
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

    prompt_outline_text = """
    You are an expert content strategist. Your task is to generate a structured article outline in English based on the topic below.
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
    # Section 2: A descriptive title for the second section
    - Talking point 1 for section 2
    """
    prompt_outline = PromptTemplate(template=prompt_outline_text, input_variables=["topic"])
    
    chain = prompt_outline | llm | StrOutputParser()
    eprint("✓ Outline Content Generator Chain has been built.")
    eprint("Generating outline content...")

    response_text = chain.invoke({"topic": topic})
    
    outline = parse_outline_from_text(response_text)
    eprint(f"✓ Outline successfully constructed and validated. Title: '{outline.title}'")

    with open(outline_output_path, "w", encoding="utf-8") as f:
        f.write(outline.model_dump_json(indent=2))
    eprint(f"✅ Outline successfully saved as: {outline_output_path}")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate a long-read article outline on a specific topic.")
    parser.add_argument("topic", type=str, help="The main topic for the outline.")
    parser.add_argument("--outline-out", type=str, required=True, help="The path to save the JSON outline.")
    args = parser.parse_args()
    
    generate_outline(args.topic, args.outline_out)