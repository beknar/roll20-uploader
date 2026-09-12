"""Official dnd5e SRD actor YAML -> payload objects.

Lets a note that says "use the stats for an Archmage" resolve to a real sheet.
Point srd_actors at a checkout of the dnd5e system repo in config.json; leave it
null and this module simply never fires.
"""
import re, yaml, json, glob, os

SIZE_WORD = {"tiny":"Tiny","sm":"Small","med":"Medium","lg":"Large","huge":"Huge","grg":"Gargantuan"}
SKILL_FULL = {"acr":"acrobatics","ani":"animalhandling","arc":"arcana","ath":"athletics",
  "dec":"deception","his":"history","ins":"insight","itm":"intimidation","inv":"investigation",
  "med":"medicine","nat":"nature","prc":"perception","prf":"performance","per":"persuasion",
  "rel":"religion","slt":"sleightofhand","ste":"stealth","sur":"survival"}
ABIL = ["str","dex","con","int","wis","cha"]
mod = lambda v: (v - 10)//2
def pb_for(cr): return max(2, 2 + max(0, int(cr) - 1)//4)
def sgn(n): return f"+{n}" if n >= 0 else str(n)

def strip_html(h):
    t = h or ""
    # keep the dice out of dnd5e roll macros: [[/damage 4d6 type=piercing]] -> "4d6 piercing"
    def dmg(m):
        inner = m.group(1)
        d = re.search(r"(\d+d\d+(?:\s*[+-]\s*\d+)?)", inner)
        ty = re.search(r"type=(\w+)", inner)
        return (d.group(1) if d else "") + (f" {ty.group(1)}" if ty else "")
    t = re.sub(r"\[\[/damage([^\]]*)\]\]", dmg, t)
    t = re.sub(r"\[\[/[^\]]*\]\]\{([^}]*)\}", r"\1", t)
    t = re.sub(r"\[\[/[^\]]*\]\]", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s{2,}", " ", t).strip()

ARMOR_DEX_CAP = {"light": 99, "medium": 2, "heavy": 0}

def derive_ac(doc, ab):
    """SRD NPCs often leave ac.flat null and derive AC from an equipped armour item."""
    s = doc["system"]
    acf = s["attributes"]["ac"]
    if acf.get("flat"): return {"value": acf["flat"],
                                "notes": acf.get("calc") if acf.get("calc") in ("natural",) else None}
    base, notes, shield = 10 + mod(ab["dex"]), None, 0
    for it in doc.get("items", []):
        isys = it.get("system", {})
        av = (isys.get("armor") or {}).get("value")
        kind = (isys.get("type") or {}).get("value")
        if it["type"] != "equipment" or not isys.get("equipped"): continue
        if kind == "shield": shield += av or 2
        elif av and kind in ARMOR_DEX_CAP:
            base = av + min(mod(ab["dex"]), ARMOR_DEX_CAP[kind]); notes = it["name"].lower()
    out = {"value": base + shield}
    if notes: out["notes"] = notes + (", shield" if shield else "")
    return out

def convert(doc):
    s = doc["system"]
    ab = {a: s["abilities"][a]["value"] for a in ABIL}
    cr = s["details"].get("cr") or 0
    pb = pb_for(cr)
    out = {
        "name": doc["name"],
        "size": SIZE_WORD.get(s["traits"].get("size", "med"), "Medium"),
        "type": (s["details"].get("type") or {}).get("value", "humanoid"),
        "alignment": s["details"].get("alignment") or "Unaligned",
        "ac": {k: v for k, v in derive_ac(doc, ab).items() if v},
        "hp": {"average": s["attributes"]["hp"]["max"], "formula": s["attributes"]["hp"].get("formula") or ""},
        "abilities": ab, "cr": str(cr), "pb": pb,
    }
    sub = (s["details"].get("type") or {}).get("subtype")
    if sub: out["type"] += f" ({sub})"
    mv = s["attributes"].get("movement") or {}
    sp = [f"{mv.get('walk',30)} ft."] + [f"{k} {mv[k]} ft." for k in ("burrow","climb","fly","swim") if mv.get(k)]
    out["speed"] = ", ".join(sp)
    saves = {a: sgn(mod(ab[a]) + pb) for a in ABIL if s["abilities"][a].get("proficient")}
    if saves: out["saves"] = saves
    sk = {}
    for k, v in (s.get("skills") or {}).items():
        if v.get("value"):
            sk[SKILL_FULL[k]] = sgn(mod(ab[v.get("ability","dex")]) + pb*v["value"])
    if sk: out["skills"] = sk
    sen = s["attributes"].get("senses") or {}
    stxt = [f"{k} {sen[k]} ft." for k in ("darkvision","blindsight","tremorsense","truesight") if sen.get(k)]
    prc = mod(ab["wis"]) + pb*((s.get("skills") or {}).get("prc", {}).get("value") or 0)
    stxt.append(f"passive Perception {10+prc}")
    out["senses"] = ", ".join(stxt)
    langs = (s["traits"].get("languages") or {})
    lt = [l.title() for l in (langs.get("value") or []) if l != "custom"]
    lt += [langs["custom"]] if langs.get("custom") else []
    if lt: out["languages"] = ", ".join(lt)
    for key, fld in (("damage_resistances","dr"), ("damage_immunities","di"),
                     ("damage_vulnerabilities","dv"), ("condition_immunities","ci")):
        t = s["traits"].get(fld) or {}
        vals = list(t.get("value") or []) + ([t["custom"]] if t.get("custom") else [])
        if vals: out[key] = ", ".join(vals)

    traits, actions, reactions, legend = [], [], [], []
    spells = {}
    for it in doc.get("items", []):
        if it["type"] == "spell":
            lvl = (it.get("system") or {}).get("level", 0)
            spells.setdefault(lvl, []).append(it["name"])
            continue
        isys = it.get("system", {})
        desc = strip_html((isys.get("description") or {}).get("value"))
        acts = isys.get("activities") or {}
        act = next(iter(acts.values()), {})
        atype = ((act.get("activation") or {}).get("type")) or ""
        if it["type"] in ("equipment", "consumable", "loot", "container", "tool"):
            continue                       # armour and gear are not NPC traits
        row = {"name": it["name"], "desc": desc}
        if it["type"] == "weapon" and act.get("type") == "attack":
            at = act.get("attack") or {}
            abil = at.get("ability") or "str"
            tohit = int(at["bonus"]) if at.get("flat") and at.get("bonus") else mod(ab.get(abil, 10)) + pb
            base = (isys.get("damage") or {}).get("base") or {}
            dmg = ""
            if base.get("number") and base.get("denomination"):
                bonus = mod(ab.get(abil, 10))
                dmg = f"{base['number']}d{base['denomination']}" + (f"+{bonus}" if bonus > 0 else (str(bonus) if bonus < 0 else ""))
            melee = ((at.get("type") or {}).get("value") or "melee") == "melee"
            a = {"type": "Melee" if melee else "Ranged", "tohit": sgn(tohit),
                 "dmg1": dmg, "type1": (base.get("types") or ["bludgeoning"])[0], "target": "one target"}
            rng = act.get("range") or {}
            if melee: a["reach"] = f"{rng.get('value') or 5} ft."
            else: a["range"] = f"{rng.get('value') or 30}/{rng.get('long') or ''} ft."
            row["attack"] = a
        if atype == "legendary": legend.append(row)
        elif atype == "reaction": reactions.append(row)
        elif atype in ("action", "bonus"): actions.append(row)
        else: traits.append(row)
    if spells:
        lines = []
        for lvl in sorted(spells):
            label = "Cantrips" if lvl == 0 else f"{lvl}{'st' if lvl==1 else 'nd' if lvl==2 else 'rd' if lvl==3 else 'th'} level"
            lines.append(f"{label}: " + ", ".join(sorted(spells[lvl])))
        sp = next((t for t in traits if t["name"].lower().startswith("spellcasting")), None)
        if sp: sp["desc"] += " — " + " | ".join(lines)
        else: traits.append({"name": "Spellcasting", "desc": " | ".join(lines)})
        slots = {}
        for lvl in sorted(spells):
            if lvl: slots[str(lvl)] = 0
        if slots: out["spell_slots"] = slots
    if traits: out["traits"] = traits
    if actions: out["actions"] = actions
    if reactions: out["reactions"] = reactions
    if legend: out["legendary"] = {"count": 3, "actions": legend}
    return out

def build_index():
    idx = {}
    from .config import CFG
    root = CFG.get("srd_actors")
    if not root:
        return {}          # no SRD checkout configured: cloning is simply unavailable
    for p in glob.glob(os.path.join(root, "*", "*.yml")) + glob.glob(os.path.join(root, "*.yml")):
        if os.path.basename(p).startswith("_"): continue
        d = yaml.safe_load(open(p, encoding="utf-8"))
        if d and d.get("type") == "npc":
            idx[re.sub(r"[^a-z0-9]", "", d["name"].lower())] = p
    return idx

if __name__ == "__main__":
    idx = build_index()
    print(f"{len(idx)} SRD actors indexed")
    if "assassin" in idx:
        print(json.dumps(convert(yaml.safe_load(open(idx["assassin"], encoding="utf-8"))), indent=1)[:1200])
