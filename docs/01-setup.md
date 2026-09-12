# 1. Setup

## Roll20 side

You need a **Pro** account — Mods (API scripts) are Pro-only.

Install the **5e NPC JSON Importer** from Roll20's script library
(Settings → Mods → Script Library). It does the actual sheet-building; this
project feeds it.

Your game must use the **D&D 5e by Roll20** character sheet — the legacy one.
The attribute and repeating-section names this project writes to are that
sheet's. A different sheet will need the field names re-derived.

## Local side

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.json config.json
```

Edit `config.json`:

```jsonc
{
  "vault": "/path/to/vault",        // the only required field
  "campaign_label": "My Campaign",  // chat sender name in the mod scripts
  "out": "build",

  "attachments": {                  // where art lives, relative to the vault
    "creatures":    "_attachments/creatures",
    "characters":   "_attachments/characters",
    "locations":    "_attachments/locations",
    "maps":         "_attachments/maps",
    "maps_generic": "_attachments/maps/generic"
  },

  "art": {
    "token_suffix": "-token-128"    // goblin.jpg -> goblin-token-128.png
  },

  "maps": {
    "feet_per_square": 10,          // old-school modules often rule at 10ft
    "scene_width_squares": 25
  },

  "srd_actors": null                // optional, see below
}
```

`config.json` is gitignored, so your paths stay out of commits. You can also
point at a config elsewhere with `R20_CONFIG=/path/to/config.json`.

### Optional: SRD stat blocks

Vault notes often say *"uses the stats of an Archmage"* rather than repeating a
stat block. Point `srd_actors` at the monsters folder of a
[dnd5e system](https://github.com/foundryvtt/dnd5e) checkout and those notes
resolve to real sheets:

```json
"srd_actors": "/path/to/dnd5e/packs/_source/monsters"
```

Leave it `null` and such notes become biography-only sheets instead.

## Vault expectations

- Notes have YAML front matter. `name` is used if present, otherwise the
  filename.
- A stat block is recognised in either convention: markdown with `**Bold**`
  labels, or a fenced plain-text block.
- Art is referenced from the note (`portrait:`, `image:` or `img:` in front
  matter). Only the filename stem matters for matching.

Nothing else about your vault's folder structure is assumed — notes are found by
walking, not by convention.

## Order of work

Each stage is independent and re-runnable. Do them in this order the first time:

1. [NPCs](02-npcs.md) — the sheets everything else attaches to
2. [Token actions](04-token-actions.md) — repair what the importer leaves broken
3. [Library URLs](08-library-urls.md) — prerequisite for art and maps
4. [Art](03-art.md) — portraits and default tokens
5. [Spells](05-spells.md) — caster spell sections
6. [Maps](06-maps.md) — pages
