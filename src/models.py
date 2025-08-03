# src/models.py
import re
from typing import List
from pydantic import BaseModel, Field

def eprint(*args, **kwargs):
    # Een kopie van eprint voor het geval het hier nodig is
    import sys
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
        parts = re.split(r'\[(TITLE|HOOK|CONCLUSION|SECTIONS)\]', text)
        
        content_map = {
            "TITLE": parts[2].strip() if len(parts) > 2 else "",
            "HOOK": parts[4].strip() if len(parts) > 4 else "",
            "CONCLUSION": parts[6].strip() if len(parts) > 6 else "",
            "SECTIONS": parts[8].strip() if len(parts) > 8 else ""
        }

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