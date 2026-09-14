"""Render 5etools spell JSON into D&D 5E by Roll20 sheet fields.

The 5etools dataset is the source of truth for spell text and properties. Point
``source_dir`` at any local copy of ``data/spells/`` (a self-hosted 5etools
mirror, a checkout of the 5etools source repo, or a directory of the same JSON
files). Nothing here is specific to one campaign.
"""
import glob
import json
import os
import re

# Roll20 spell names that differ from the 5etools name.
DEFAULT_ALIASES = {"acid arrow": "melf's acid arrow"}

SCHOOLS = {'A': 'abjuration', 'C': 'conjuration', 'D': 'divination', 'E': 'enchantment',
           'V': 'evocation', 'I': 'illusion', 'N': 'necromancy', 'T': 'transmutation'}

# Every field this module fills. Order matters only for readability.
FIELDS = ['spelllevel', 'spellschool', 'spellritual', 'spellcastingtime', 'spellrange',
          'spellcomp_v', 'spellcomp_s', 'spellcomp_m', 'spellcomp_materials',
          'spellconcentration', 'spellduration', 'spelldescription', 'spellathigherlevels',
          'spelloutput', 'spellattack', 'spelldamage', 'spelldamagetype', 'spelldamagetype2',
          'spelldamage2', 'spellhealing', 'spelldmgmod', 'spell_damage_progression', 'spellsave',
          'spellsavesuccess', 'spellhldie', 'spellhldietype']

TAG = re.compile(r'\{@(\w+)\s*([^}]*)\}')
_SOURCEY = ('PHB', 'XGE', 'DMG', 'MM', 'TCE', 'SCC', 'GGR', 'FTD', 'XPHB', 'XDMG', 'XMM')
_LINKISH = {'spell', 'creature', 'item', 'condition', 'skill', 'action', 'sense', 'status',
            'table', 'variantrule', 'deity', 'language', 'background', 'race', 'class',
            'feat', 'object', 'optfeature', 'hazard', 'reward', 'disease', 'vehicle',
            'cult', 'boon', 'charoption', 'psionic', 'trap', 'legroup'}


def load_spells(source_dir):
    """Return {lowercased spell name: spell dict} for every spells-*.json in source_dir."""
    idx = {}
    for path in sorted(glob.glob(os.path.join(source_dir, 'spells-*.json'))):
        with open(path, encoding='utf-8') as fh:
            for spell in json.load(fh).get('spell', []):
                idx.setdefault(spell['name'].lower(), spell)
    return idx


def strip_tags(text):
    """Flatten 5etools {@tag ...} markup to plain text."""
    def rep(m):
        tag, parts = m.group(1), m.group(2).split('|')
        if tag in ('damage', 'dice'):
            return parts[0]
        if tag in ('scaledamage', 'scaledice'):
            return parts[-1]
        if tag == 'dc':
            return 'DC ' + parts[0]
        if tag == 'chance':
            return parts[0] + ' percent'
        if tag == 'hit':
            return '+' + parts[0]
        if len(parts) > 1 and tag in _LINKISH:
            return parts[-1] if not parts[-1].startswith(_SOURCEY) else parts[0]
        return parts[0]
    prev = None
    while prev != text:
        prev, text = text, TAG.sub(rep, text)
    return text


def render_entries(entries):
    """Render a 5etools entry tree to plain text suitable for a Roll20 text field."""
    out = []
    for e in entries:
        if isinstance(e, str):
            out.append(strip_tags(e))
            continue
        if not isinstance(e, dict):
            continue
        kind = e.get('type')
        if kind == 'list':
            for item in e.get('items', []):
                if isinstance(item, str):
                    out.append('• ' + strip_tags(item))
                elif isinstance(item, dict):
                    name = strip_tags(item.get('name', '')) if item.get('name') else ''
                    sub = item.get('entries') or ([item['entry']] if item.get('entry') else [])
                    out.append('• ' + (name + '. ' if name else '') + render_entries(sub))
        elif kind == 'table':
            rows = []
            if e.get('colLabels'):
                rows.append(' | '.join(strip_tags(str(c)) for c in e['colLabels']))
            for row in e.get('rows', []):
                cells = []
                for c in row:
                    if isinstance(c, dict):
                        c = c.get('roll', {}).get('exact', c.get('entry', ''))
                    cells.append(strip_tags(str(c)))
                rows.append(' | '.join(cells))
            caption = strip_tags(e.get('caption', ''))
            out.append((caption + '\n' if caption else '') + '\n'.join(rows))
        elif kind in ('entries', 'inset', 'insetReadaloud', 'section', 'quote'):
            name = strip_tags(e.get('name', '')) if e.get('name') else ''
            out.append((name + '. ' if name else '') + render_entries(e.get('entries', [])))
        elif e.get('entries'):
            out.append(render_entries(e['entries']))
    return '\n'.join(x for x in out if x)


def casting_time(spell):
    t = spell['time'][0]
    unit = 'bonus action' if t['unit'] == 'bonus' else t['unit']
    return '%d %s' % (t['number'], unit if t['number'] == 1 else unit + 's')


def spell_range(spell):
    r = spell['range']
    kind = r['type']
    dist = r.get('distance') or {}
    dtype, amount = dist.get('type'), dist.get('amount')
    if kind == 'special':
        return 'Special'
    if kind == 'point':
        simple = {'self': 'Self', 'touch': 'Touch', 'sight': 'Sight',
                  'unlimited': 'Unlimited', 'plane': 'Unlimited (same plane)'}
        if dtype in simple:
            return simple[dtype]
        if dtype == 'feet':
            return '%d feet' % amount
        if dtype == 'miles':
            return '%d %s' % (amount, 'mile' if amount == 1 else 'miles')
        return str(dtype)
    if dtype == 'self' or amount is None:
        return 'Self'
    return 'Self (%d-%s %s)' % (amount, 'foot' if dtype == 'feet' else 'mile', kind)


def components(spell):
    c = spell.get('components') or {}
    v = '{{v=1}}' if c.get('v') else '0'
    s = '{{s=1}}' if c.get('s') else '0'
    m = c.get('m')
    if not m:
        return v, s, '0', ''
    text = m if isinstance(m, str) else (m.get('text') or '')
    return v, s, '{{m=1}}', strip_tags(text)


def duration(spell):
    d = spell['duration'][0]
    kind = d['type']
    conc = bool(d.get('concentration'))
    if kind == 'instant':
        text = 'Instantaneous'
    elif kind == 'special':
        text = 'Special'
    elif kind == 'permanent':
        ends = d.get('ends', [])
        if 'dispel' in ends and 'trigger' in ends:
            text = 'Until dispelled or triggered'
        elif 'dispel' in ends:
            text = 'Until dispelled'
        else:
            text = 'Permanent'
    else:
        inner = d.get('duration', {})
        amount, unit = inner.get('amount'), inner.get('type')
        text = '%d %s' % (amount, unit if amount == 1 else unit + 's')
        if conc:
            text = 'Up to ' + text
    return text, ('{{concentration=1}}' if conc else '0')


_DMG = re.compile(r'\{@damage\s+([^}|]+)')
_DICE = re.compile(r'\{@dice\s+([^}|]+)')
_SCALE = re.compile(r'\{@scale(?:damage|dice)\s+[^|]*\|[^|]*\|([^}|]+)')


# "4d6 fire damage and 4d6 radiant damage" - both land, so the sheet gets two dice.
_ADDITIVE = re.compile(
    r'(\d+d\d+)\s+(\w+)\s+damage,?\s+and\s+(\d+d\d+)\s+(\w+)\s+damage', re.I)
# "3d8 radiant damage (if you are good or neutral) or 3d8 necrotic damage" - pick one.
_ALIGNED = re.compile(
    r'\d+d\d+\s+(\w+)\s+damage\s*\(if you are good or neutral\)\s*or\s+'
    r'\d+d\d+\s+(\w+)\s+damage', re.I)


def _damage_bits(spell, desc):
    """Return (damage, type, damage2, type2, healing, evil_type).

    A second damage line is filled in only when the spell deals both at once.
    Spells that offer a choice of type (Fire Shield) or vary by the caster's
    alignment (Spirit Guardians) keep a single damage line; the alternative is
    returned separately so the mod can swap it per caster.
    """
    raw = json.dumps(spell.get('entries', []))
    hit = _DMG.search(raw)
    damage = hit.group(1).strip() if hit else ''
    types = spell.get('damageInflict') or []

    # 5etools marks healing spells with the HL misc tag. Trust that rather than
    # reading the text: "the target can't regain hit points" (Chill Touch) reads
    # exactly like a heal to any regex loose enough to catch the real ones.
    healing = ''
    if 'HL' in (spell.get('miscTags') or []):
        h = _DICE.search(raw) or _DMG.search(raw)
        if h:
            healing = h.group(1).strip()
    # A pure healing spell has no damage line; one that does both (Vampiric
    # Touch) keeps them separate.
    if healing and healing == damage and not types:
        damage = ''

    dtype = types[0].capitalize() if types else ''
    dmg2 = dtype2 = evil = ''

    aligned = _ALIGNED.search(desc)
    add = _ADDITIVE.search(desc)
    if aligned:
        dtype, evil = aligned.group(1).capitalize(), aligned.group(2).capitalize()
    elif add:
        damage, dtype = add.group(1), add.group(2).capitalize()
        dmg2, dtype2 = add.group(3), add.group(4).capitalize()
    elif len(types) > 1:
        # Two types listed but only one is dealt on any given cast (Fire Shield).
        # Prefer the one the text actually rolls damage for.
        m = re.search(r'%s\s+(\w+)\s+damage' % re.escape(damage), desc, re.I) if damage else None
        if m and m.group(1).lower() in [t.lower() for t in types]:
            dtype = m.group(1).capitalize()

    return damage, dtype, dmg2, dtype2, healing, evil


def build_row(spell, roll20_name):
    """Return the dict of Roll20 sheet fields for one spell."""
    desc = render_entries(spell.get('entries', []))
    higher = re.sub(r'^At Higher Levels\.\s*', '',
                    render_entries(spell.get('entriesHigherLevel', [])))
    v, s, m, materials = components(spell)
    dur, conc = duration(spell)
    level = spell['level']
    damage, dtype, damage2, dtype2, healing, evil_type = _damage_bits(spell, desc)

    attacks = spell.get('spellAttack') or []
    attack = 'Ranged' if 'R' in attacks else ('Melee' if 'M' in attacks else 'None')

    saves = spell.get('savingThrow') or []
    save = saves[0].capitalize() if saves else ''
    save_success = 'Half damage' if save and re.search(r'half as much damage', desc, re.I) else ''

    dmgmod = 'Yes' if re.search(
        r'(hit points equal to|damage equal to)[^.]{0,60}spellcasting ability modifier',
        desc, re.I) else '0'

    hldie = hldietype = ''
    scaled = _SCALE.search(json.dumps(spell.get('entries', [])) +
                           json.dumps(spell.get('entriesHigherLevel', [])))
    if scaled and level > 0:
        mm = re.match(r'(\d*)d(\d+)', scaled.group(1).strip())
        if mm:
            hldie, hldietype = (mm.group(1) or '1'), 'd' + mm.group(2)

    return {
        'spellname': roll20_name,
        'spelllevel': 'cantrip' if level == 0 else str(level),
        'spellschool': SCHOOLS[spell['school']],
        'spellritual': '{{ritual=1}}' if (spell.get('meta') or {}).get('ritual') else '0',
        'spellcastingtime': casting_time(spell),
        'spellrange': spell_range(spell),
        'spellcomp_v': v, 'spellcomp_s': s, 'spellcomp_m': m,
        'spellcomp_materials': materials,
        'spellconcentration': conc,
        'spellduration': dur,
        'spelldescription': desc,
        'spellathigherlevels': higher,
        # ATTACK whenever the row produces a roll; SPELLCARD when it is text only.
        'spelloutput': 'ATTACK' if (attack != 'None' or damage or healing) else 'SPELLCARD',
        'spellattack': attack,
        'spelldamage': damage, 'spelldamagetype': dtype,
        'spelldamage2': damage2, 'spelldamagetype2': dtype2,
        # consumed by the mod, not written to the sheet as-is:
        'alt_evil_damagetype': evil_type,
        'spellhealing': healing,
        'spelldmgmod': dmgmod,
        'spell_damage_progression': 'Cantrip Dice' if (level == 0 and (damage or healing)) else '',
        'spellsave': save, 'spellsavesuccess': save_success,
        'spellhldie': hldie, 'spellhldietype': hldietype,
    }


def build_table(names, source_dir, aliases=None):
    """Build {normalised name: fields} for the given spell names.

    Returns (table, missing) so callers can report names with no dataset match.
    """
    aliases = dict(DEFAULT_ALIASES, **(aliases or {}))
    idx = load_spells(source_dir)
    table, missing = {}, []
    for name in names:
        spell = idx.get(aliases.get(name.lower(), name.lower()))
        if not spell:
            missing.append(name)
            continue
        row = build_row(spell, name)
        fields = {k: row[k] for k in FIELDS}
        # only carried for the handful of spells whose damage type follows the
        # caster's alignment; the mod resolves it per character
        if row.get('alt_evil_damagetype'):
            fields['alt_evil_damagetype'] = row['alt_evil_damagetype']
        table[re.sub(r'[^a-z0-9]', '', name.lower())] = fields
    return table, missing
