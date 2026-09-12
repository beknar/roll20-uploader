"""Vault notes -> 5e_NPC_JSON_Importer payload objects."""
import os, re, json, glob, html
from . import vault as llcore
from . import statblock as SB
from .vault import load_note, section, drop_sections, to_html, iter_notes, slug

SIZE_WORD = {"tiny":"Tiny","sm":"Small","med":"Medium","lg":"Large","huge":"Huge","grg":"Gargantuan"}
XP = {0:10, 0.125:25, 0.25:50, 0.5:100, 1:200, 2:450, 3:700, 4:1100, 5:1800, 6:2300, 7:2900,
      8:3900, 9:5000, 10:5900, 11:7200, 12:8400, 13:10000, 14:11500, 15:13000, 16:15000,
      17:18000, 18:20000, 19:22000, 20:25000, 21:33000, 22:41000, 23:50000, 24:62000,
      25:75000, 26:90000, 27:105000, 28:120000, 29:135000, 30:155000}
SKILL_FULL = {"acr":"acrobatics","ani":"animalhandling","arc":"arcana","ath":"athletics",
  "dec":"deception","his":"history","ins":"insight","itm":"intimidation","inv":"investigation",
  "med":"medicine","nat":"nature","prc":"perception","prf":"performance","per":"persuasion",
  "rel":"religion","slt":"sleightofhand","ste":"stealth","sur":"survival"}

def cr_str(cr):
    return {0.125:"1/8", 0.25:"1/4", 0.5:"1/2"}.get(cr, str(int(cr)) if cr == int(cr) else str(cr))

def ac_obj(sb):   # note: uses plain(), defined below
    m = re.search(r"\(([^)]*)\)", sb.get("ac_txt", ""))
    return {"value": sb["ac"], "notes": plain(m.group(1))} if m else {"value": sb["ac"]}

def plain(text):
    """Markdown-ish stat block prose -> plain text for Roll20 descriptions."""
    t = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    t = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\s*\n\s*", " ", t)
    return re.sub(r"\s{2,}", " ", t).strip()

def attack_obj(atk):
    a = {"type": "Melee" if atk["melee"] else "Ranged",
         "tohit": f"+{atk['tohit']}" if atk["tohit"] >= 0 else str(atk["tohit"]),
         "dmg1": f"{atk['dnum']}d{atk['ddie']}" + (f"+{atk['dbonus']}" if atk["dbonus"] > 0
                 else (str(atk["dbonus"]) if atk["dbonus"] < 0 else "")),
         "type1": atk["dtype"]}
    if atk["melee"] and atk.get("reach"): a["reach"] = f"{atk['reach']} ft."
    if atk.get("rng"):
        a["range"] = f"{atk['rng']}/{atk['rlong']} ft." if atk.get("rlong") else f"{atk['rng']} ft."
    a["target"] = "one target"
    return a

def entries_to(sb, zone):
    out = []
    for e in sb["entries"]:
        if e["zone"] != zone: continue
        row = {"name": e["name"], "desc": plain(e["text"])}
        if zone in ("actions", "reactions", "bonus actions"):
            atk = SB.parse_attack(e["text"])
            if atk: row["attack"] = attack_obj(atk)
        out.append(row)
    return out

SPELL_SLOTS = re.compile(r"(\d)(?:st|nd|rd|th)\s*(?:level)?\s*\((\d+)\s*slots?\)", re.I)

def spellcasting(sb):
    tr = next((e for e in sb["entries"] if e["name"].lower().startswith("spellcasting")), None)
    if not tr: return {}
    t = tr["text"]
    out = {}
    m = re.search(r"\b(Intelligence|Wisdom|Charisma)\b", t)
    if m: out["spellcasting_ability"] = m.group(1)[:3].lower()
    m = re.search(r"(\d+)(?:st|nd|rd|th)[- ]level (?:spell)?caster", t, re.I)
    if m: out["caster_level"] = int(m.group(1))
    slots = {lvl: int(n) for lvl, n in SPELL_SLOTS.findall(t)}
    if slots: out["spell_slots"] = {str(k): v for k, v in sorted(slots.items())}
    return out

def detag(h):
    """Plain text only. The payload travels through a Roll20 handout, whose notes are
    rich text — any markup we leave in gets parsed by Roll20 and shredded, taking the
    surrounding JSON with it (real newlines inside a JSON string = unparseable)."""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h or "", flags=re.S | re.I)
    t = re.sub(r"<li[^>]*>", " • ", t)
    t = re.sub(r"</(p|div|h[1-6]|li|tr)>", " ", t)
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "(")
          .replace("&gt;", ")").replace("&quot;", "'").replace("&#39;", "'"))
    t = re.sub(r"[\r\n\t]+", " ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t.replace("<", "(").replace(">", ")")

def bio_for(fm, body, name):
    b = drop_sections(body, ["Stat Block (5e 2014)",
                             "Stat Block (Pathfinder 1e original, kept for reference)"])
    bits = []
    for k, label in (("occupation","Occupation"), ("challenge_rating","CR"),
                     ("conversion","Conversion"), ("source","Source")):
        if fm.get(k): bits.append(f"{label}: {fm[k]}")
    head = " | ".join(bits)
    txt = detag(to_html(b, None, name))
    return (head + " — " + txt if head else txt)[:4000]

def build(path, fm, body):
    name = fm.get("name") or os.path.basename(path)[:-3]
    sec = section(body, "Stat Block (5e 2014)")
    sb = SB.parse(sec) if sec else None
    if not sb: return None, name
    cr = sb["cr"]
    d = {
        "name": name,
        "size": SIZE_WORD.get(sb["size"], "Medium"),
        "type": sb["ctype"] + (f" ({sb['subtype']})" if sb.get("subtype") else ""),
        "alignment": sb.get("alignment") or "Unaligned",
        "ac": ac_obj(sb),
        "hp": {"average": sb["hp"], "formula": sb["hp_formula"]} if sb["hp_formula"] else sb["hp"],
        "speed": sb["speed_txt"],
        "abilities": sb["abilities"],
        "cr": cr_str(cr),
        "xp": XP.get(cr, 0),
        "pb": sb["pb"] or max(2, 2 + max(0, int(cr) - 1)//4),
        "init_tiebreaker": "@{dexterity}/100",
        "bio": bio_for(fm, body, name),
    }
    if sb["saves"]:
        d["saves"] = {a: (f"+{v}" if v >= 0 else str(v)) for a, v in sb["saves"].items()}
    if sb["skills"]:
        d["skills"] = {SKILL_FULL[k]: (f"+{v}" if v >= 0 else str(v)) for k, v in sb["skills"].items()}
    for key, src in (("damage_resistances","dr_txt"), ("damage_immunities","di_txt"),
                     ("damage_vulnerabilities","dv_txt"), ("condition_immunities","ci_txt")):
        if sb.get(src): d[key] = sb[src]
    sen = sb["senses"]
    stxt = ", ".join(f"{k} {sen[k]} ft." for k in ("darkvision","blindsight","tremorsense","truesight") if sen[k])
    pp = 10 + (sb["abilities"]["wis"] - 10)//2 + (sb["skills"].get("prc", 0) and 0)
    m = re.search(r"passive Perception (\d+)", sec)
    if m: stxt = (stxt + ", " if stxt else "") + f"passive Perception {m.group(1)}"
    if stxt: d["senses"] = stxt
    langs, custom = sb["languages"]
    ltxt = ", ".join([l.title() for l in langs] + ([custom] if custom else []))
    if ltxt: d["languages"] = ltxt
    for z, key in (("trait","traits"), ("actions","actions"),
                   ("bonus actions","bonus_actions"), ("reactions","reactions")):
        rows = entries_to(sb, z)
        if rows: d[key] = rows
    legs = entries_to(sb, "legendary actions")
    if legs: d["legendary"] = {"count": 3, "actions": legs}
    d.update(spellcasting(sb))
    return d, name

# --- resolving "Statistics as MM <X>" notes -------------------------------
STAT_AS = re.compile(r"Statistics as (?:the Monster Manual |MM |a |an |the )?"
                     r"\*\*(?:\[\[)?([^\]*|]+?)(?:\|[^\]]+)?(?:\]\])?\*\*", re.I)
BASE_RE = re.compile(r"Monster Manual \(2014\)\s+([A-Za-z'\u2019\- ]+?)\s*(?:p\.\d+|;|$)", re.I)

def resolve_base(fm, statsec):
    c = []
    m = STAT_AS.search(statsec)
    if m: c.append(m.group(1).strip())
    cs = fm.get("conversion_source") or ""
    m = BASE_RE.search(cs)
    if m: c.append(m.group(1).strip())
    c += [x.strip() for x in re.findall(r"\[\[([^\]|]+)", cs)]
    c += [x.strip() for x in re.findall(r"\[\[([^\]|]+)", statsec)]
    seen = []
    for x in c:
        if x and x not in seen: seen.append(x)
    return seen

BOLD_AC = re.compile(r"(?:\*\*AC\s*(\d+)\*\*|AC\s*\*\*(\d+)\*\*)")
BOLD_HP = re.compile(r"(?:\*\*HP\s*(\d+)[^*]*\*\*|HP\s*\*\*(\d+)[^*]*\*\*)")

def clone_from(base, fm, body, name, statsec):
    import copy
    d = copy.deepcopy(base)
    d["name"] = name
    cr = SB.cr_val((fm.get("challenge_rating") or "").replace("CR", "").replace("(5e)", ""))
    if cr:
        d["cr"] = cr_str(cr); d["xp"] = XP.get(cr, d.get("xp", 0))
        d["pb"] = max(2, 2 + max(0, int(cr) - 1)//4)
    m = BOLD_AC.search(statsec)
    if m: d["ac"] = {"value": int(m.group(1) or m.group(2)), "notes": "adjusted"}
    m = BOLD_HP.search(statsec)
    if m: d["hp"] = int(m.group(1) or m.group(2))
    delta = plain(re.sub(r"^>.*$", "", statsec, flags=re.M))
    d["bio"] = (f"Built on the {base['name']} stat block. "
                f"Vault notes: {detag(delta)[:1200]} — " + bio_for(fm, body, name))
    return d

def main():
    out, skipped, cloned = [], [], []
    pending = []
    for sub in ("Creatures", "Characters/NPCs"):
        for p, fm, body in iter_notes(sub):
            d, name = build(p, fm, body)
            if d: out.append(d)
            else: pending.append((p, fm, body, name))

    import yaml
    from . import srdbase as srd2roll20
    srd_idx = srd2roll20.build_index()
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    srd_cache = {}
    def srd(nm):
        k = norm(nm)
        if k not in srd_idx: return None
        if k not in srd_cache:
            srd_cache[k] = srd2roll20.convert(yaml.safe_load(open(srd_idx[k], encoding="utf-8")))
        return srd_cache[k]

    by_name = {slug(d["name"]): d for d in out}
    for p, fm, body, name in pending:
        statsec = section(body, "Stat Block (5e 2014)")
        hit = base_label = None
        for c in resolve_base(fm, statsec):          # candidate order: "Statistics as X" wins
            if slug(c) in by_name: hit, base_label = by_name[slug(c)], f"vault: {c}"; break
            b = srd(c)
            if b: hit, base_label = b, f"SRD {c}"; break
        if hit:
            out.append(clone_from(hit, fm, body, name, statsec))
            cloned.append((name, base_label))
        else:
            # deities, hazards and non-combat NPCs: a named sheet with biography only
            out.append({"name": name, "size": "Medium",
                        "type": (fm.get("creature_type") or "humanoid"),
                        "alignment": "Unaligned",
                        "bio": "No mechanical stat block in the vault — narrative entry. "
                               + bio_for(fm, body, name)})
            skipped.append(name)
    print(f"cloned from a vault creature: {len(cloned)}")
    for n, b in cloned: print(f"    {n} <- {b}")
    from .config import out_path
    json.dump(out, open(out_path("npcs.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(skipped, open(out_path("skipped.json"), "w"), indent=1)
    tot = sum(len(json.dumps(d)) for d in out)
    print(f"converted {len(out)} NPCs   ({tot/1024:.0f} KB of JSON)")
    print(f"bio-only (no stat block, by design): {len(skipped)} -> {skipped}")

if __name__ == "__main__":
    main()
