# 5. Spells

```bash
python src/build_spells.py      # -> build/LL_Spells.js
```

```
!llspells test [name]   # one caster
!llspells apply         # all of them
!llspells status        # what is populated
!llspells revert        # delete the rows this script created
```

## What it fills

- spells filed under the right level (`repeating_spell-cantrip`, `-1` … `-9`)
- each spell's school
- slot totals per level (`lvl1_slots_total` …)
- save DC, spell attack bonus, casting ability
- innate casters get their usage ("at will", "3/day") in the innate field

**Names and levels only — no descriptions.** Most vaults carry spell names, not
spell text, and there is no SRD spell source wired in. Clicking a spell gives
you its name and level. Slot tracking, which is the part that affects play,
works properly.

## Parsing

Four trait formats are handled, because books use all of them:

```
Cantrips (at will): light, sacred flame   1st level (4 slots): bane, command
Cantrips: light, sacred flame. 1st (4): bane, command. 2nd (3): hold person
At will: sacred flame. 3/day: cure wounds. 1/day: flame strike
Signatures: at will guidance; 3/day cure wounds; 1/day hold person
```

Slot-based casters get their slot counts from the text. Innate casters have
usage rather than slots, so their spells need a level from somewhere:
`src/r20/data/spell_levels.json` supplies it for common SRD spells. Anything not
in that file is **reported, not guessed** — add it and re-run.

## Two gotchas

**Blank is not neutral.** Leaving `spellschool` empty makes the sheet default
that dropdown to Abjuration *and save it*, so every spell ends up filed as
Abjuration. `src/r20/data/spell_schools.json` supplies real schools; unknowns are
listed at the end of the build so you can extend it.

**Sheets cloned from an SRD base carry their spell list twice** — once from the
vault note and once from the base. Rows are deduped by level+name and the union
is kept.

## Re-running

`apply` updates rows already present rather than duplicating them, so it is safe
to re-run after extending the school or level tables.
