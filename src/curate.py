#!/usr/bin/env python3
"""
Curates the raw data from raw.json.
- Filters out items with an impact score below a threshold.
- Sorts the remaining items by impact, descending.
- Saves the result to curated.json.
Call: python -m src.curate
"""
import json

# --- Configuratie ----------------------------------------------------
INPUT_FILE = "raw.json"
OUTPUT_FILE = "curated.json"
MINIMUM_IMPACT_SCORE = 7  # Alleen nieuws met deze score of hoger wordt meegenomen
# ---------------------------------------------------------------------

# Lees de ruwe data
try:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"❌ Fout bij het lezen van {INPUT_FILE}. Zorg dat het bestand bestaat en valide JSON is. Fout: {e}")
    exit(1)

# Filter de data op basis van de impact score
# .get('impact', 0) zorgt ervoor dat het script niet crasht als een item geen 'impact' heeft.
curated_data = [
    item for item in data if item.get('impact', 0) >= MINIMUM_IMPACT_SCORE
]

# Sorteer de gefilterde data van hoge naar lage impact
curated_data.sort(key=lambda item: item.get('impact', 0), reverse=True)

# Sla de gecureerde data op
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(curated_data, f, indent=2, ensure_ascii=False)

print(f"✅ Data gecureerd. {len(curated_data)} van de {len(data)} items zijn relevant en opgeslagen in {OUTPUT_FILE}.")
