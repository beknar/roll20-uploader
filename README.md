# roll20-uploader

Bulk-import a TTRPG campaign from a markdown vault into Roll20: NPC sheets with
working attack rolls, portraits and default tokens, spell lists, and map pages
with the grid aligned.

Built against an [Obsidian](https://obsidian.md) vault of D&D 5e (2014) content
and the **D&D 5e by Roll20** legacy character sheet, on a Roll20 **Pro** account
(Mods/API required). Nothing in it is specific to one campaign — paths, labels
and scale all come from `config.json`.

## What it produces

| Script | What it does | Needs |
|---|---|---|
| `LL_Payload_1..N.js` + `LL_Importer.js` | Creates NPC sheets, paced so the importer keeps up | [5e NPC JSON Importer](#prerequisites) |
| `LL_Fix.js` | Repairs the token action macros the importer leaves broken | — |
| `LL_Art.js` | Sets each character's avatar and default token | art uploaded, URLs harvested |
| `LL_Spells.js` | Fills the sheet's spell section and slot totals | — |
| `LL_SpellData.js` | Fills in the rest of each spell row: text, properties, and roll fields | a local 5etools `data/spells` |
| `LL_SpellAtk.js` | Token-action buttons for the spells that need an attack roll | `LL_SpellData.js` run first |
| `LL_SpellLink.js` | Links ATTACK spell rows to generated attack rows so they roll | `LL_SpellData.js` run first |
| `LL_Maps.js` | Configures pages and places map images | art uploaded, blank pages made |

## The shape of it

```
vault (markdown + images)
        |
        |  python: parse stat blocks, spells, map grids
        v
   build/*.json  ---->  build/LL_*.js   (Roll20 mod scripts)
        ^                      |
        |                      |  paste into Roll20 -> Mods
   library.json                v
   (harvested from      chat commands: !llimport, !llfix,
    your art library)    !llart, !llspells, !llmaps
```

Two things force this shape, and both are Roll20 constraints rather than design
choices:

1. **The Mod API cannot reference an image that Roll20 does not already host.**
   So art must be uploaded by hand first, and its URLs harvested from the
   browser before any script can use them.
2. **The Mod API cannot create pages.** It can configure existing ones. So blank
   pages are made from the browser console and `LL_Maps.js` adopts them.

## Quick start

```bash
git clone <this repo> && cd roll20-uploader
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.json config.json                # then edit "vault"
```

```bash
python src/extract_npcs.py      # vault -> build/npcs.json
python src/build_npcs.py        # -> LL_Payload_*.js + LL_Importer.js
```

Paste those into Roll20 (Settings → Mods), then in chat:

```
!llimport test        # one NPC, check the sheet
!llimport start       # the rest
!llfix apply          # repair the token actions
```

Art, spells and maps each have their own pass. Work through
[`docs/`](docs/) in order — every stage has a `test` command that does one item
so you can look before committing to hundreds.

## Prerequisites

- **Roll20 Pro** — Mods (API scripts) are a Pro feature.
- **[5e NPC JSON Importer](https://github.com/Roll20/roll20-api-scripts)** installed as a Mod.
  It needs a one-line edit; see [docs/02-npcs.md](docs/02-npcs.md#the-guard-edit).
- **D&D 5e by Roll20** sheet (the legacy one, not Jumpgate's rebuild).
- Python 3.10+.

## Vault expectations

A note becomes an NPC if it has YAML front matter and a markdown stat block.
Two stat block conventions are parsed: `**Bold Label**` markdown and fenced
plain-text blocks. Art is matched by filename stem — a note pointing at
`goblin.jpg` wants `goblin` and `goblin-token-128` in your Roll20 library.

Notes with no stat block still produce a sheet carrying the narrative text. That
is deliberate: deities, hazards and townsfolk have no stats in most books, and a
sheet saying so beats a missing entry.

## What it does not do

- **Spell descriptions.** Names, levels, schools and slots only. Most vaults
  carry spell names, not spell text.
- **Walls, dynamic lighting, or door placement.**
- **Automatic grid alignment on every map.** It is reliable about pitch when a
  printed grid exists, and honest about not knowing otherwise — see
  [docs/07-grid-detection.md](docs/07-grid-detection.md). Expect to align a
  handful by hand.
- **Journal handouts.** Not built yet.

## Licence

The code here is yours to use. The campaign content it processes is not — this
imports material you already own into a VTT you already pay for.
