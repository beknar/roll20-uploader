"""Parse a gm-apprentice '## Stat Block (5e 2014)' markdown block into structured data."""
import re

SIZE = {"tiny":"tiny","small":"sm","medium":"med","large":"lg","huge":"huge","gargantuan":"grg"}
SKILL = {"acrobatics":"acr","animal handling":"ani","arcana":"arc","athletics":"ath","deception":"dec",
 "history":"his","insight":"ins","intimidation":"itm","investigation":"inv","medicine":"med","nature":"nat",
 "perception":"prc","performance":"prf","persuasion":"per","religion":"rel","sleight of hand":"slt",
 "stealth":"ste","survival":"sur"}
ABIL = ["str","dex","con","int","wis","cha"]
LANG = {"common":"common","dwarvish":"dwarvish","elvish":"elvish","giant":"giant","gnomish":"gnomish",
 "goblin":"goblin","halfling":"halfling","orc":"orc","abyssal":"abyssal","celestial":"celestial",
 "draconic":"draconic","deep speech":"deep","infernal":"infernal","primordial":"primordial",
 "sylvan":"sylvan","undercommon":"undercommon","aquan":"aquan","auran":"auran","ignan":"ignan",
 "terran":"terran","druidic":"druidic","thieves' cant":"cant"}
DMG = ["acid","bludgeoning","cold","fire","force","lightning","necrotic","piercing","poison",
 "psychic","radiant","slashing","thunder"]
COND = ["blinded","charmed","deafened","diseased","exhaustion","frightened","grappled","incapacitated",
 "invisible","paralyzed","petrified","poisoned","prone","restrained","stunned","unconscious"]

def _n(s):
    s = s.replace("−","-").replace("–","-").replace("—","-")
    return s

def _int(s, d=0):
    try: return int(_n(s))
    except Exception: return d

def cr_val(s):
    s = _n(s or "").strip()
    m = re.match(r"(\d+)\s*/\s*(\d+)", s)
    if m: return int(m.group(1))/int(m.group(2))
    m = re.match(r"(\d+)", s)
    return int(m.group(1)) if m else 0

def strip_quotes(sb):
    return re.sub(r"^>.*$", "", sb, flags=re.M)

def parse(sb):
    """Return dict or None if not a full block."""
    t = _n(strip_quotes(sb))
    t = re.split(r"^###\s", t, maxsplit=1, flags=re.M)[0]
    out = {}
    m = re.search(r"^\*\*Armor Class\*\*\s*(.+)$", t, re.M)
    if not m: return None
    ac_txt = m.group(1).strip()
    am = re.search(r"(\d+)", ac_txt)
    out["ac"] = _int(am.group(1)) if am else 10
    out["ac_txt"] = ac_txt

    m = re.search(r"^\*\*Hit Points\*\*\s*(\d+)\s*(?:\(([^)]+)\))?", t, re.M)
    if not m: return None
    out["hp"] = _int(m.group(1)); out["hp_formula"] = (m.group(2) or "").strip()

    m = re.search(r"^\*\*Speed\*\*\s*(.+)$", t, re.M)
    out["speed_txt"] = m.group(1).strip() if m else "30 ft."
    mv = {"walk":0,"burrow":0,"climb":0,"fly":0,"swim":0,"hover":False,"units":"ft"}
    st = out["speed_txt"].lower()
    w = re.match(r"\s*(\d+)\s*ft", st)
    if w: mv["walk"] = int(w.group(1))
    for k in ("burrow","climb","fly","swim"):
        mm = re.search(k + r"\s*(\d+)\s*ft", st)
        if mm: mv[k] = int(mm.group(1))
    if "hover" in st: mv["hover"] = True
    out["movement"] = mv

    # ability table row
    am = re.search(r"^\|\s*(-?\d+)\s*\([^)]*\)\s*\|\s*(-?\d+)\s*\([^)]*\)\s*\|\s*(-?\d+)\s*\([^)]*\)\s*\|"
                   r"\s*(-?\d+)\s*\([^)]*\)\s*\|\s*(-?\d+)\s*\([^)]*\)\s*\|\s*(-?\d+)\s*\([^)]*\)\s*\|", t, re.M)
    if not am: return None
    out["abilities"] = {a: _int(am.group(i+1), 10) for i, a in enumerate(ABIL)}

    # type / alignment line: *Medium humanoid (human), lawful evil*
    tm = re.search(r"^\*(Tiny|Small|Medium|Large|Huge|Gargantuan)\s+([a-z ]+?)(?:\s*\(([^)]*)\))?,\s*(.+?)\*$",
                   t, re.M | re.I)
    if tm:
        out["size"] = SIZE.get(tm.group(1).lower(), "med")
        out["ctype"] = tm.group(2).strip().lower()
        out["subtype"] = (tm.group(3) or "").strip()
        out["alignment"] = tm.group(4).strip().title()
        sw = re.match(r"swarm of (tiny|small|medium|large) (.+)", out["ctype"])
        if sw:
            out["swarm"] = SIZE.get(sw.group(1), "tiny"); out["ctype"] = sw.group(2).rstrip("s")
    else:
        out["size"] = "med"; out["ctype"] = "humanoid"; out["subtype"] = ""; out["alignment"] = ""

    m = re.search(r"^\*\*Challenge\*\*\s*([0-9/]+)", t, re.M)
    out["cr"] = cr_val(m.group(1)) if m else 0
    m = re.search(r"Proficiency Bonus\*?\*?\s*\+?(\d+)", t)
    out["pb"] = _int(m.group(1), 2) if m else None

    m = re.search(r"^\*\*Saving Throws\*\*\s*(.+)$", t, re.M)
    out["saves"] = {}
    if m:
        for a, b in re.findall(r"\b(Str|Dex|Con|Int|Wis|Cha)\s*([+-]\d+)", m.group(1)):
            out["saves"][a.lower()] = int(b)

    m = re.search(r"^\*\*Skills\*\*\s*(.+)$", t, re.M)
    out["skills"] = {}
    if m:
        for nm, b in re.findall(r"([A-Za-z][A-Za-z ']*?)\s*([+-]\d+)", m.group(1)):
            k = SKILL.get(nm.strip().lower())
            if k: out["skills"][k] = int(b)

    def lst(label, vocab):
        mm = re.search(r"^\*\*" + label + r"\*\*\s*(.+)$", t, re.M)
        if not mm: return [], ""
        raw = mm.group(1).lower()
        vals = [v for v in vocab if re.search(r"\b" + re.escape(v) + r"\b", raw)]
        return vals, mm.group(1).strip()
    out["dr"], out["dr_txt"] = lst("Damage Resistances", DMG)
    out["di"], out["di_txt"] = lst("Damage Immunities", DMG)
    out["dv"], out["dv_txt"] = lst("Damage Vulnerabilities", DMG)
    out["ci"], out["ci_txt"] = lst("Condition Immunities", COND)

    m = re.search(r"^\*\*Senses\*\*\s*(.+)$", t, re.M)
    sen = {"darkvision":0,"blindsight":0,"tremorsense":0,"truesight":0,"units":"ft","special":""}
    if m:
        low = m.group(1).lower()
        for k in ("darkvision","blindsight","tremorsense","truesight"):
            mm = re.search(k + r"\s*(\d+)", low)
            if mm: sen[k] = int(mm.group(1))
    out["senses"] = sen

    m = re.search(r"^\*\*Languages\*\*\s*(.+)$", t, re.M)
    langs, lcustom = [], ""
    if m:
        raw = m.group(1)
        low = raw.lower()
        for name, key in LANG.items():
            if re.search(r"\b" + re.escape(name) + r"\b", low): langs.append(key)
        known = set(LANG)
        rest = [p.strip() for p in re.split(r"[,;]", re.sub(r"\*", "", raw))
                if p.strip() and p.strip().lower() not in known
                and p.strip() not in ("-", "\u2014", "\u2013")]
        lcustom = "; ".join(rest)
    out["languages"] = (sorted(set(langs)), lcustom)

    # ---- entries ----
    body_start = 0
    mm = re.search(r"^\*\*Challenge\*\*.*$", t, re.M)
    if mm: body_start = mm.end()
    rest = t[body_start:]

    heads = list(re.finditer(r"^\*\*(Actions|Reactions|Legendary Actions|Bonus Actions|Lair Actions|Gear)\*\*\s*$",
                             rest, re.M))
    zones = []
    prev_end, prev_name = 0, "trait"
    for h in heads:
        zones.append((prev_name, rest[prev_end:h.start()]))
        prev_name = h.group(1).lower(); prev_end = h.end()
    zones.append((prev_name, rest[prev_end:]))

    entries = []
    for zone, chunk in zones:
        for em in re.finditer(r"\*\*\*([^*]+?)\.?\*\*\*\s*(.*?)(?=\n\*\*\*|\n\*\*[A-Z]|\Z)", chunk, re.S):
            name = em.group(1).strip().rstrip(".")
            text = em.group(2).strip()
            entries.append({"zone": zone, "name": name, "text": text})
    out["entries"] = entries
    out["preamble"] = re.split(r"^\*\*Actions\*\*", rest, flags=re.M)[0]
    return out

ATTACK = re.compile(
    r"\*(Melee|Ranged|Melee or Ranged)\s+(Weapon|Spell)\s+Attack:\*\s*([+-]\d+)\s*to hit"
    r"(?:,\s*(?:reach\s*(\d+)\s*ft\.?)?\s*(?:(?:or\s*)?range\s*(\d+)\s*/\s*(\d+)\s*ft\.?)?)?"
    r"[^.]*\.\s*\*Hit:\*\s*(?:\d+\s*)?\(?\s*(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?\s*\)?\s*([a-z]+)\s+damage", re.I)

def parse_attack(text):
    m = ATTACK.search(text.replace("−","-").replace("–","-"))
    if not m: return None
    kind, cls, tohit, reach, rmin, rmax, dn, dd, sign, dbon, dtype = m.groups()
    return dict(melee=kind.lower().startswith("melee"), ranged="ranged" in kind.lower(),
                classification="weapon" if cls.lower()=="weapon" else "spell",
                tohit=int(tohit), reach=int(reach) if reach else None,
                rng=int(rmin) if rmin else None, rlong=int(rmax) if rmax else None,
                dnum=int(dn), ddie=int(dd),
                dbonus=(int(dbon) * (-1 if sign=="-" else 1)) if dbon else 0,
                dtype=dtype.lower())


# ---------------------------------------------------------------------------
# Plain-text stat blocks inside a ``` fence (The Slumbering Tsar convention)
# ---------------------------------------------------------------------------
FENCE = re.compile(r"```[a-z]*\n(.*?)```", re.S)
ZONE_HEAD = re.compile(r"^(ACTIONS|REACTIONS|BONUS ACTIONS|LEGENDARY ACTIONS|LAIR ACTIONS|"
                       r"MYTHIC ACTIONS|VILLAIN ACTIONS|REGIONAL EFFECTS)\s*$", re.M)
ENTRY = re.compile(r"^([A-Z][A-Za-z0-9'’/\- ]{0,58}?(?:\s*\([^)]{0,40}\))?)\.\s+(.*)$", re.S)

def _unwrap(block):
    """Hard-wrapped prose -> one paragraph per blank-line-separated chunk."""
    out = []
    for para in re.split(r"\n\s*\n", block):
        p = re.sub(r"\s*\n\s*", " ", para).strip()
        if p: out.append(p)
    return out

def parse_plain(sb):
    m = FENCE.search(sb)
    if not m: return None
    t = _n(m.group(1))
    out = {}

    am = re.search(r"^Armor Class\s+(.+)$", t, re.M)
    hm = re.search(r"^Hit Points\s+(\d+)\s*(?:\(([^)]+)\))?", t, re.M)
    ab = re.findall(r"\b(STR|DEX|CON|INT|WIS|CHA)\s+(\d+)\s*\([+-]?\d+\)", t)
    if not (am and hm and len(ab) >= 6): return None

    out["ac_txt"] = am.group(1).strip()
    n = re.search(r"(\d+)", out["ac_txt"]); out["ac"] = _int(n.group(1)) if n else 10
    out["hp"] = _int(hm.group(1)); out["hp_formula"] = (hm.group(2) or "").strip()
    out["abilities"] = {k.lower(): _int(v, 10) for k, v in ab[:6]}

    sm = re.search(r"^Speed\s+(.+)$", t, re.M)
    out["speed_txt"] = sm.group(1).strip() if sm else "30 ft."
    mv = {"walk": 0, "burrow": 0, "climb": 0, "fly": 0, "swim": 0, "hover": False, "units": "ft"}
    st = out["speed_txt"].lower()
    w = re.match(r"\s*(\d+)\s*ft", st)
    if w: mv["walk"] = int(w.group(1))
    for k in ("burrow", "climb", "fly", "swim"):
        mm = re.search(k + r"\s*(\d+)\s*ft", st)
        if mm: mv[k] = int(mm.group(1))
    if "hover" in st: mv["hover"] = True
    out["movement"] = mv

    # "Large giant, chaotic evil"  (line 2 of the block)
    head = [l.strip() for l in t.strip().splitlines() if l.strip()][:2]
    tm = re.match(r"(Tiny|Small|Medium|Large|Huge|Gargantuan)\s+([a-z ]+?)(?:\s*\(([^)]*)\))?,\s*(.+)$",
                  head[1] if len(head) > 1 else "", re.I)
    if tm:
        out["size"] = SIZE.get(tm.group(1).lower(), "med")
        out["ctype"] = tm.group(2).strip().lower()
        out["subtype"] = (tm.group(3) or "").strip()
        out["alignment"] = tm.group(4).strip().title()
        sw = re.match(r"swarm of (tiny|small|medium|large) (.+)", out["ctype"])
        if sw:
            out["swarm"] = SIZE.get(sw.group(1), "tiny"); out["ctype"] = sw.group(2).rstrip("s")
    else:
        out["size"] = "med"; out["ctype"] = "humanoid"; out["subtype"] = ""; out["alignment"] = ""

    cm = re.search(r"^Challenge\s+([0-9/]+)", t, re.M)
    out["cr"] = cr_val(cm.group(1)) if cm else 0
    pm = re.search(r"Proficiency Bonus\s*\+?(\d+)", t)
    out["pb"] = _int(pm.group(1), 2) if pm else None

    out["saves"] = {}
    sv = re.search(r"^Saving Throws\s+(.+)$", t, re.M)
    if sv:
        for a, b in re.findall(r"\b(Str|Dex|Con|Int|Wis|Cha)\s*([+-]\d+)", sv.group(1)):
            out["saves"][a.lower()] = int(b)
    out["skills"] = {}
    sk = re.search(r"^Skills\s+(.+)$", t, re.M)
    if sk:
        for nm, b in re.findall(r"([A-Za-z][A-Za-z ']*?)\s*([+-]\d+)", sk.group(1)):
            k = SKILL.get(nm.strip().lower())
            if k and k not in out["skills"]: out["skills"][k] = int(b)

    def lst(label, vocab):
        mm = re.search(r"^" + label + r"\s+(.+)$", t, re.M)
        if not mm: return [], ""
        raw = mm.group(1).lower()
        return [v for v in vocab if re.search(r"\b" + re.escape(v) + r"\b", raw)], mm.group(1).strip()
    out["dr"], out["dr_txt"] = lst("Damage Resistances", DMG)
    out["di"], out["di_txt"] = lst("Damage Immunities", DMG)
    out["dv"], out["dv_txt"] = lst("Damage Vulnerabilities", DMG)
    out["ci"], out["ci_txt"] = lst("Condition Immunities", COND)

    sen = {"darkvision": 0, "blindsight": 0, "tremorsense": 0, "truesight": 0, "units": "ft", "special": ""}
    sm2 = re.search(r"^Senses\s+(.+)$", t, re.M)
    if sm2:
        low = sm2.group(1).lower()
        for k in ("darkvision", "blindsight", "tremorsense", "truesight"):
            mm = re.search(k + r"\s*(\d+)", low)
            if mm: sen[k] = int(mm.group(1))
    out["senses"] = sen

    langs, lcustom = [], ""
    lm = re.search(r"^Languages\s+(.+)$", t, re.M)
    if lm:
        raw = lm.group(1); low = raw.lower()
        for name, key in LANG.items():
            if re.search(r"\b" + re.escape(name) + r"\b", low): langs.append(key)
        known = set(LANG)
        rest = [p.strip() for p in re.split(r"[,;]", raw)
                if p.strip() and p.strip().lower() not in known
                and p.strip() not in ("-", "—", "–")]
        lcustom = "; ".join(rest)
    out["languages"] = (sorted(set(langs)), lcustom)

    # everything after the Challenge line is traits + zoned actions
    tail = t[cm.end():] if cm else t
    tail = re.sub(r"^.*$", "", tail, count=1, flags=re.M)     # rest of the Challenge line
    cuts, zones = [], []
    pos, zone = 0, "trait"
    for zm in ZONE_HEAD.finditer(tail):
        zones.append((zone, tail[pos:zm.start()])); zone = zm.group(1).lower(); pos = zm.end()
    zones.append((zone, tail[pos:]))

    entries = []
    for zname, chunk in zones:
        for para in _unwrap(chunk):
            em = ENTRY.match(para)
            if not em: continue
            name = em.group(1).strip()
            if name.isupper() and len(name) > 3: continue
            entries.append({"zone": zname, "name": name, "text": em.group(2).strip()})
    out["entries"] = entries
    out["preamble"] = ""
    return out

_parse_md = parse
def parse(sb):
    """Try the markdown convention first, then the fenced plain-text one."""
    d = _parse_md(sb)
    return d if d else parse_plain(sb)

# plain-text attacks carry no asterisks
ATTACK_PLAIN = re.compile(
    r"(Melee|Ranged|Melee or Ranged)\s+(Weapon|Spell)\s+Attack:\s*([+-]\d+)\s*to hit"
    r"(?:,\s*(?:reach\s*(\d+)\s*ft\.?)?\s*(?:(?:or\s*)?range\s*(\d+)\s*/\s*(\d+)\s*ft\.?)?)?"
    r"[^.]*\.\s*Hit:\s*(?:\d+\s*)?\(?\s*(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?\s*\)?\s*([a-z]+)\s+damage", re.I)

_parse_attack_md = parse_attack
def parse_attack(text):
    d = _parse_attack_md(text)
    if d: return d
    m = ATTACK_PLAIN.search(text.replace("−", "-").replace("–", "-"))
    if not m: return None
    kind, cls, tohit, reach, rmin, rmax, dn, dd, sign, dbon, dtype = m.groups()
    return dict(melee=kind.lower().startswith("melee"), ranged="ranged" in kind.lower(),
                classification="weapon" if cls.lower() == "weapon" else "spell",
                tohit=int(tohit), reach=int(reach) if reach else None,
                rng=int(rmin) if rmin else None, rlong=int(rmax) if rmax else None,
                dnum=int(dn), ddie=int(dd),
                dbonus=(int(dbon) * (-1 if sign == "-" else 1)) if dbon else 0,
                dtype=dtype.lower())
