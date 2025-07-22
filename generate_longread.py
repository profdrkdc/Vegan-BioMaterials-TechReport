import os
import argparse
import time
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate

# --- 1. Datastructuren voor de Outline ---
class ArticleSection(BaseModel):
    title: str = Field(description="De titel van deze sectie van het artikel.")
    talking_points: List[str] = Field(
        description="Een lijst met 3-5 kernpunten, vragen of onderwerpen die in deze sectie behandeld moeten worden."
    )

class ArticleOutline(BaseModel):
    title: str = Field(description="Een pakkende, SEO-vriendelijke titel voor het volledige artikel.")
    introduction_hook: str = Field(description="Een korte zin of een pakkend idee om de introductie mee te beginnen.")
    sections: List[ArticleSection] = Field(description="De lijst met de te schrijven secties van het artikel.")
    conclusion_summary: str = Field(description="Een korte samenvatting van de hoofdgedachte voor de conclusie.")


# --- 2. Functie om de volledige LangChain-pijplijn te bouwen en uit te voeren ---
def generate_longread_article(topic: str, output_path: str):
    """
    Bouwt en voert een volledige LangChain-pijplijn uit om een long-read artikel te genereren.
    Deze versie werkt SEQUENTIEEL om rate limits te vermijden.
    """
    print("AI-pijplijn gestart (sequentiële modus)...")

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.7, top_p=0.9)
    print(f"Model geïnitialiseerd: {llm.model}")

    # --- KETEN 1: Outline Generation ---
    parser_outline = PydanticOutputParser(pydantic_object=ArticleOutline)
    prompt_outline = PromptTemplate(
        template="""
Je bent een expert content strateeg, gespecialiseerd in diepgaande analyses van vegan biotech en food-tech.
Je taak is om een gedetailleerde, logisch gestructureerde outline te creëren voor een diepgaand artikel (ca. 1500-2000 woorden) op basis van het opgegeven onderwerp.
Onderwerp: {topic}
De outline moet de lezer van een algemeen overzicht naar specifieke details en een toekomstvisie leiden.
Zorg voor een pakkende titel en een lijst van secties met specifieke, inhoudelijke gesprekspunten.
{format_instructions}
""",
        input_variables=["topic"],
        partial_variables={"format_instructions": parser_outline.get_format_instructions()},
    )
    chain_outline = prompt_outline | llm | parser_outline
    print("✓ Keten 1 (Outline) is gebouwd.")

    # --- KETEN 2: Section Writing (per sectie) ---
    prompt_section = PromptTemplate.from_template(
        """
Je bent een getalenteerde schrijver die complexe onderwerpen helder en boeiend kan uitleggen.
Schrijf een gedetailleerde en goed onderbouwde sectie voor een groter artikel, gebaseerd op de volgende instructies.
Sectie Titel: {title}
Kernpunten om te behandelen: {talking_points}
Schrijf ongeveer 300-400 woorden. Zorg voor een vlotte, informatieve en professionele stijl.
Schrijf de output direct in Markdown. Gebruik geen extra kopteksten voor de sectie zelf, enkel de pure tekst.
---
SECTION CONTENT:"""
    )
    chain_section_writer = prompt_section | llm | StrOutputParser()
    print("✓ Keten 2 (Section Writer) is gebouwd.")

    # --- KETEN 3: Synthesis (samenvoegen tot eindartikel) ---
    prompt_synthesis = PromptTemplate.from_template(
        """
Jij bent de eindredacteur. Je taak is om de volgende, los geschreven secties samen te voegen tot een enkel, coherent en publicatieklaar long-read artikel.
Artikel Titel: {title}
Context voor Introductie: {introduction_hook}
Context voor Conclusie: {conclusion_summary}
Hier zijn de volledig geschreven secties:
---
{sections_text}
---
Jouw taken:
1.  Schrijf een pakkende, overkoepelende introductie (ca. 150-200 woorden). Gebruik de 'Context voor Introductie' als inspiratie.
2.  Voeg de aangeleverde secties naadloos aan elkaar. Zorg voor vloeiende overgangen waar nodig, maar verander de kern van de secties niet.
3.  Schrijf een krachtige conclusie (ca. 150-200 woorden) die de belangrijkste punten samenvat en een blik op de toekomst werpt. Gebruik de 'Context voor Conclusie' als basis.
4.  Formatteer het volledige eindresultaat als een enkel, coherent Markdown-document. Begin met de hoofdtitel (H1: # Titel). Gebruik H2 (##) voor de sectietitels.
FINAAL ARTIKEL:
"""
    )
    chain_synthesis = prompt_synthesis | llm | StrOutputParser()
    print("✓ Keten 3 (Synthesis) is gebouwd.")
    print("-" * 50)


    # --- Uitvoering (Stap voor stap) ---
    print("Stap 1: Outline genereren...")
    outline = chain_outline.invoke({"topic": topic})
    print(f"✓ Outline ontvangen met {len(outline.sections)} secties.")
    print("-" * 50)

    print("Stap 2: Secties schrijven (één voor één)...")
    written_sections = []
    for i, section in enumerate(outline.sections):
        print(f"  -> Sectie {i+1}/{len(outline.sections)} schrijven: '{section.title}'")
        # --- CODE WIJZIGING HIER ---
        # .dict() is verouderd, we gebruiken nu .model_dump()
        section_text = chain_section_writer.invoke(section.model_dump())
        written_sections.append(section_text)
        time.sleep(2)

    print("✓ Alle secties zijn geschreven.")
    print("-" * 50)

    print("Stap 3: Eindredactie en synthese...")
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
    print("✓ Synthese voltooid!")
    print("-" * 50)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_article)
    print(f"✅ Artikel succesvol opgeslagen als: {output_path}")


# --- Hoofdingang van het script ---
if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Genereer een long-read artikel over een specifiek onderwerp met LangChain.")
    parser.add_argument("topic", type=str, help="Het hoofdonderwerp van het artikel.")
    parser.add_argument("-o", "--output", type=str, default="longread_output.md", help="Het pad naar het output Markdown-bestand.")
    parser.add_argument("--api-key", type=str, help="Optioneel: Google AI API key. Overschrijft de environment variable.")
    args = parser.parse_args()

    if args.api_key:
        os.environ["GOOGLE_API_KEY"] = args.api_key
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("Fout: Google API Key niet gevonden.")
        print("Stel de GOOGLE_API_KEY environment variable in, of geef hem mee met --api-key.")
        exit(1)

    generate_longread_article(args.topic, args.output)