"""Stage 5: fill the sheet's spell section for NPC casters.

    python src/build_spells.py

Reads the Spellcasting / Innate Spellcasting trait text out of npcs.json, parses
it into spells filed by level, and emits LL_Spells.js.

Four shapes of trait text are handled, because books use all of them:
    Cantrips (at will): a, b   1st level (4 slots): c, d
    Cantrips: a, b. 1st (4): c, d. 2nd (3): e
    At will: a, b. 3/day: c. 1/day: d
    Signatures: at will a, b; 3/day c; 1/day d

Slot-based casters get their slot totals as well, which is the half that
actually changes play. Innate casters have usage ("3/day") instead of slots, so
their spells need a level from somewhere -- r20/data/spell_levels.json supplies
it for common SRD spells and anything missing is reported, not guessed.

NAMES AND LEVELS ONLY. Descriptions are not filled in: most vaults do not carry
spell text, and inventing it would be worse than leaving it blank.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r20.config import REPO, out_path
from _tmpl import render

DATA = os.path.join(REPO, "src", "r20", "data")
SCHOOLS = {k.lower(): v for k, v in json.load(open(os.path.join(DATA, "spell_schools.json"))).items()}
INNATE_LEVEL = json.load(open(os.path.join(DATA, "spell_levels.json")))

LVL = re.compile(r'(?:(Cantrips?)\s*(?:\(at\s*will\))?|(\d)(?:st|nd|rd|th)(?:\s*level)?\s*'
                 r'(?:\(\s*(\d+)\s*(?:slots?)?\s*\))?)\s*:\s*', re.I)
INN = re.compile(r'(At\s*will|\d+\s*/\s*day(?:\s*each)?)\s*:?\s*', re.I)
DC  = re.compile(r'(?:spell\s*save\s*DC|save\s*DC)\s*(\d+)', re.I)
ABL = re.compile(r'\b(Wisdom|Intelligence|Charisma)\b', re.I)
ABBR = {"wisdom": "wis", "intelligence": "int", "charisma": "cha"}

def segments(text, rx):
    out, ms = [], list(rx.finditer(text))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out.append((m, text[m.end():end]))
    return out

def spell_names(blob):
    blob = re.split(r'[|;•]|\s—\s', blob)[0]
    blob = re.split(r'(?<=[a-z])\.(?:\s|$)', blob)[0]
    names = []
    for p in blob.split(','):
        p = re.sub(r'\([^)]*\)', '', p).strip(' .;*•|—')
        if p and len(p) < 40 and not re.search(r'\d|:', p):
            names.append(p.lower())
    return names

def caster_rows(npc):
    traits = [t for t in npc.get("traits", [])
              if 'astin' in t.get("name", "") or 'Innate' in t.get("name", "")]
    if not traits:
        return None, []
    text = '. '.join(t.get("desc", "").rstrip(' .') for t in traits)
    dc = DC.search(text)
    atk = re.search(r'\+(\d+)\s*(?:to hit|\))', text)
    ab = ABL.search(text)
    entry = {"n": npc["name"],
             "dc": int(dc.group(1)) if dc else 0,
             "atk": int(atk.group(1)) if atk else 0,
             "ab": ABBR.get(ab.group(1).lower(), "") if ab else "",
             "slots": {}, "sp": []}
    unknown = []
    seen = set()
    levelled = segments(text, LVL)
    pairs = []
    if levelled:
        for m, blob in levelled:
            lvl = 'cantrip' if m.group(1) else m.group(2)
            if m.group(3):
                entry["slots"][lvl] = int(m.group(3))
            for s in spell_names(blob):
                pairs.append((lvl, s, ""))
    else:
        for m, blob in segments(text, INN):
            use = re.sub(r'\s+', ' ', m.group(1)).lower()
            for s in spell_names(blob):
                lvl = INNATE_LEVEL.get(s)
                if not lvl:
                    unknown.append(s); continue
                pairs.append((lvl, s, use))
    for lvl, s, use in pairs:
        if (lvl, s) in seen:          # SRD-cloned sheets can carry the list twice
            continue
        seen.add((lvl, s))
        entry["sp"].append([lvl, s.title(), use, SCHOOLS.get(s, "")])
    return entry, unknown

def main():
    npcs = json.load(open(out_path("npcs.json"), encoding="utf-8"))
    rows, unknown, noschool = [], [], set()
    for npc in npcs:
        e, unk = caster_rows(npc)
        if not e or not e["sp"]:
            continue
        unknown += [(npc["name"], u) for u in unk]
        noschool |= {s[1] for s in e["sp"] if not s[3]}
        rows.append(json.dumps(e, separators=(",", ":")))
    render("LL_Spells.js.tmpl", rows, "LL_Spells.js")
    if unknown:
        print(f"\n{len(unknown)} innate spells with no known level "
              f"(add them to src/r20/data/spell_levels.json):")
        for n, s in unknown[:30]:
            print(f"    {n:<28} {s}")
    if noschool:
        print(f"\n{len(noschool)} spells with no school on file "
              f"(add them to src/r20/data/spell_schools.json, or the sheet will "
              f"default the dropdown to Abjuration):")
        print("    " + ", ".join(sorted(noschool)[:30]))

if __name__ == "__main__":
    main()
