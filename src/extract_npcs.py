"""Stage 1: read the vault, write npcs.json.

    python src/extract_npcs.py

Walks every note in the configured vault, parses any 5e stat block it finds, and
writes one JSON object per NPC in the shape 5e_NPC_JSON_Importer expects.

Notes with no stat block still produce a sheet -- name, size, type and the
narrative text as biography. That is deliberate: deities, hazards and townsfolk
have no stats in most books, and a sheet that says so is more useful at the
table than a missing entry.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r20 import npcs

if __name__ == "__main__":
    npcs.main()
