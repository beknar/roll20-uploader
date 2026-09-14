# 10. Spell detail

`build_spells.py` (stage 5) gets each caster's spells filed under the right level
with working slot totals, but every row stops at its name. This stage fills in
the rest of the row.

```bash
python src/build_spelldata.py     # -> build/LL_SpellData.js
```

```
!llspelldata ping      # confirm it loaded, and how many casters it can see
!llspelldata report    # per caster: row count and any names it can't match
!llspelldata test      # run against the first caster only
!llspelldata run       # run against all of them
```

Run `report` before `run`. It changes nothing and tells you exactly which spell
names have no match in the dataset, which is the only thing that can silently
under-fill a sheet.

## What it fills

| Field | From |
|---|---|
| `spelldescription`, `spellathigherlevels` | rendered spell text |
| `spellritual` | `{{ritual=1}}` or `0` |
| `spellcastingtime`, `spellrange`, `spellduration` | `1 bonus action`, `Self (15-foot cone)`, `Up to 1 minute` |
| `spellcomp_v` / `_s` / `_m` / `_materials` | `{{v=1}}` style flags plus the material text |
| `spellconcentration` | `{{concentration=1}}` or `0` |
| `spell_ability` | the caster's own `spellcasting_ability`, as `@{wisdom_mod}+` |
| `innate` | the sheet's small grey marker, for casters listed in `innate` |
| `spelloutput` | `ATTACK` or `SPELLCARD` — see below |
| `spellattack`, `spelldamage`, `spelldamagetype`, `spellhealing`, `spelldmgmod`, `spell_damage_progression`, `spellsave`, `spellsavesuccess`, `spellhldie`, `spellhldietype` | the roll half of an `ATTACK` row |

It also sets `spelllevel` and `spellschool` from the dataset rather than trusting
what is already there, which repairs schools guessed by an earlier stage.

## ATTACK vs SPELLCARD

A row is **ATTACK** when clicking it should roll something — an attack roll, damage,
or healing. Everything else is **SPELLCARD**, which posts the description without
a roll. Concretely:

- attack roll (`Guiding Bolt`) → ATTACK, `spellattack = Ranged`
- save for damage (`Fireball`) → ATTACK, `spellattack = None`, `spellsave = Dexterity`
- healing (`Cure Wounds`) → ATTACK, `spellhealing = 1d8`, `spelldmgmod = Yes`
- save, no damage (`Blindness/Deafness`) → SPELLCARD, save still recorded
- pure utility (`Detect Magic`) → SPELLCARD

Damaging cantrips get `spell_damage_progression = Cantrip Dice` so they scale on
their own. Levelled spells get `spellhldie` / `spellhldietype` from the spell's
own upcasting line, so the sheet's "cast at what level" prompt scales correctly.

`spelldmgmod = Yes` is set only where the text actually says the spellcasting
modifier is added (`Cure Wounds`, `Spiritual Weapon`), not for every damaging spell.

## Where the spell text comes from

A local [5etools](https://5e.tools) dataset. Point `spell_data` in `config.json`
at any copy of its `data/spells/` directory:

```json
"spell_data": "/path/to/5etools/data/spells",
"casters": "casters.json"
```

A self-hosted mirror works (`http://localhost/data/spells/` served from disk), as
does a checkout of the 5etools source repo. The loader reads every
`spells-*.json` it finds, so you control which books are in scope by which files
you put there. For a 2014 campaign, `spells-phb.json` plus `spells-xge.json` and
`spells-tce.json` is the usual set — leave `spells-xphb.json` out or the 2024
rewrites will win.

Nothing is invented. A spell with no dataset match is named in the build output
and skipped, and `!llspelldata report` names it again from inside Roll20.

## casters.json

```json
{
  "casters": ["Example Priest", "Example Archmage"],
  "innate":  ["Example Archmage"],
  "aliases": { "acid arrow": "melf's acid arrow" },
  "spells":  ["Bless", "Cure Wounds", "Fireball"]
}
```

`casters` is matched against character names in Roll20. `innate` is the subset
whose stat block reads *Innate Spellcasting* rather than *Spellcasting*.
`aliases` covers the handful of spells Roll20 and 5etools name differently.
`spells` only decides what gets baked into the payload — the Mod matches rows by
name at run time, so a longer list is harmless.

## Gotchas

**The sheet has no Innate control.** `innate` is a free-text span that the sheet
shows in small grey type after the spell name, hidden when empty. This stage
writes the word `innate` for innate casters and leaves it empty otherwise.
Writing `{{innate=1}}` there — by analogy with the component flags — would
display that literal text on every spell.

**Checkbox fields are not booleans.** `spellritual`, `spellconcentration` and the
component flags store the roll-template fragment (`{{ritual=1}}`) when on and the
string `0` when off. Writing `1` turns them on but corrupts the roll output.

**`spelloutput = ATTACK` does not create the linked attack row.** Verified on a
live sheet: writing the whole field set through the API leaves `rollcontent` and
`spellattackid` absent and creates no `repeating_attack` row — the sheet worker
that normally builds that linkage only runs when the row is edited in the sheet
UI. The practical effect is that the row carries every correct value and posts a
full spell card, but does not roll the attack or damage dice by itself. Opening
the row in the sheet once settles it.

This is a Roll20 sheet-worker limitation rather than something the API can set
directly; closing it would mean generating the `repeating_attack` rows too and
pointing `rollcontent` at them, the same trick `LL_Fix.js` uses for NPC actions.

## Attack buttons

Stage 5b fills the spell rows, but a row with `spelloutput = ATTACK` still posts a
card rather than rolling (see the gotcha above). For the spells that need an
actual attack roll, `build_spellatk.py` sidesteps that by giving each one its own
token action.

```bash
python src/build_spellatk.py      # -> build/LL_SpellAtk.js
```

```
!llspellatk report   # what it would create, changes nothing
!llspellatk test     # first caster that has an attack-roll spell
!llspellatk run      # all of them
!llspellatk revert   # remove only the abilities this script created
```

Only rows whose `spellattack` is `Ranged` or `Melee` get a button. Save-based
spells and healing are skipped — there is no attack roll to make, and their card
already carries the detail. In practice that is a small number: a caster with 27
spells may only have two that need a button.

The macro reads `@{spell_attack_bonus}` from the caster's own sheet rather than
baking a number in, so it stays right if the NPC's stats change. It uses the same
`npcfullatk` roll template as the sheet's weapon actions, so the output matches
the NPC's other attacks. `revert` only removes abilities that are both named
after one of that caster's attack spells and built from this template, so
hand-written abilities survive.

### One to watch in the parsing

Row ids never contain an underscore — Roll20's `generateRowID` swaps them for
dashes. Allowing `_` in the id pattern makes the capture ambiguous, because the
greedy id then eats part of the field name: `repeating_spell-cantrip_-ABC_spell_damage_progression`
parses as id `-ABC_spell_damage_progressio`, field `n`. Symptoms are subtle —
fields read back empty for no obvious reason.

### Healing detection

Use the dataset's `HL` misc tag, not the spell text. "The target can't regain hit
points" (Chill Touch) reads exactly like a heal to any regex loose enough to
catch the real ones, and the result is a damage cantrip filed as healing with no
damage dice.

## Making the rows roll

Stage 5b fills the fields but a row with `spelloutput = ATTACK` still posts a
plain card, for the sheet-worker reason described above. Stage 5d closes that by
building the linked attack row itself.

```bash
python src/build_spelllink.py     # -> build/LL_SpellLink.js
```

```
!llspelllink report   # what it would link, changes nothing
!llspelllink test     # first caster with an ATTACK row
!llspelllink run      # all of them
!llspelllink revert   # delete the attack rows and unlink the spells
```

For each `ATTACK` row it creates a `repeating_attack` row and points the spell's
`rollcontent` at it, reproducing what the sheet builds when you edit a spell by
hand:

- attack-roll spells get `atkflag = {{attack=1}}` and roll `@{d20} + spell_attack_bonus`
- save spells get `atkbonus = DC<n>`, the save ability and the success effect
- upcastable spells get the `?{Cast at what level?}` prompt in `hldmg`, offering
  the spell's own level up to 9th and adding the right number of dice
- two-damage spells fill `dmg2base` / `dmg2type`
- healing rows roll as `Healing`, adding the casting modifier where the spell says to

`SPELLCARD` rows are left alone — they keep posting their description.

Everything is read off the sheet at run time, so this script carries no spell
data and does not care which books you used. Re-running refreshes existing rows
rather than duplicating them; rows are matched by the `spellid` they carry.

### Two details that have to match the sheet

`spelllevel` on the attack row is the plain level — `3`, or `cantrip` — not an
ordinal. And `spellid` / the `repeating_attack` reference inside `rollcontent`
are **lowercased**: Roll20 lowercases repeating-section ids in macro references,
so a mixed-case id in the macro will not resolve.

### A note on rows the sheet built earlier

Any spell row you had already opened in the sheet has an attack row the worker
made, and `run` refreshes those in place. Two things change for the better on
NPCs: the attack roll switches from a hardcoded `+ 3[INT] + 3[PROF]` to
`spell_attack_bonus`, so it tracks the stat block; and cantrip damage stops using
the PC formula `[[round((@{level} + 1) / 6 + 0.5)]]d10`, which depends on a
`level` attribute NPC sheets do not have, in favour of the flat dice the stat
block specifies.

### Upcast ladders

Most spells gain a die at every slot level above their own, but not all, and
getting this wrong quietly inflates damage. 5etools encodes the ladder as the
middle field of `{@scaledamage}`:

```
Cure Wounds        {@scaledice 1d8|1-9|1d8}          every level
Disintegrate       {@scaledamage 10d6 + 40|6-9|3d6}  every level, 3 dice at a time
Spiritual Weapon   {@scaledamage 1d8|2,4,6,8|1d8}    every TWO levels
```

`build_spelllink.py` reads those and passes any non-standard ladder into the mod,
which offers the correct multiplier per level — so Spiritual Weapon cast at 5th
is still +1d8, not +3d8:

```
Level 2,0|Level 3,0|Level 4,1|Level 5,1|Level 6,2|Level 7,2|Level 8,3|Level 9,3
```

Spells absent from the override are assumed to step at every level. The ladder
data needs `spell_data` in `config.json`; without it the mod falls back to
per-level for everything, which is right for all but a handful of spells.

### Build stamps

A version taken from `casters.json` alone cannot tell two builds apart: edit a
template, rebuild, and the new file claims the same version as the old one. The
builders therefore append a short hash of the template plus every value fed into
it, so the stamp only repeats when the generated script is byte-identical:

```
Build: v3 (2026-09-14, build 055b78c)
```

`!llspelllink ping` reports it, along with how many upcast ladder overrides are
baked in — which is the quickest way to confirm Roll20 has the build you think
it has, since `report` output can look identical across builds that differ.
