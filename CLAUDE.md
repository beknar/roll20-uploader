# CLAUDE.md

Notes for Claude (or any AI agent) working in this repo. Read this before
changing anything under `mods/` or `src/`.

## What this project is

A one-way pipeline: markdown vault → JSON → Roll20 Mod scripts → chat commands
that build sheets, art, spells and map pages. It exists because Roll20's Mod API
is powerful enough to create hundreds of characters but blocked from two things
that matter (image hosting and page creation), and the workarounds for those are
most of the design.

## Architecture

```
src/r20/config.py     every path comes from config.json; nothing is hardcoded
src/r20/vault.py      front matter + markdown -> notes
src/r20/statblock.py  stat block text -> structured fields (two conventions)
src/r20/npcs.py       notes -> npcs.json in importer shape
src/r20/srdbase.py    "stats as an Archmage" -> a real sheet, from an SRD checkout
src/grid/*            grid pitch detection and map region finding
src/build_*.py        json -> mod scripts, by filling mods/templates/*.tmpl
mods/                 scripts with no generated data (ship as-is)
browser/              console snippets for the two things Mods cannot do
```

Templates carry two markers: `@@DATA@@` (the generated array) and `@@LABEL@@`
(chat sender name). `src/_tmpl.py` fills them.

## Hard-won constraints — do not re-derive these

**`sendChat` throws on macro syntax.** Any string containing `@{...}`, `[[...]]`
or `{{...}}` will crash Roll20's chat parser and kill the handler mid-run with
no output. Every `say()` in these scripts defangs those before sending. If you
add a new script, copy that helper. This cost two silent failures.

**`%{...}` is an ability call, not an attribute call.** The NPC importer writes
token actions as `%{Name|repeating_npcaction_<rowid>_rollbase}`, which can never
resolve — `rollbase` is an attribute. The `$N` index form fails too; `%{}`
strips it. `LL_Fix.js` fixes this by copying the row's `rollbase` *into* the
ability and rewriting its row-relative `@{name}` references to fully-qualified
`@{repeating_npcaction_<rowid>_name}`. That needs no row context and works.

**`character.set('defaulttoken', json)` does nothing.** It does not throw; it
just fails to register a token, and Roll20 falls back to the avatar at 1×1. The
working route is `createObj('graphic', ...)` off-canvas →
`setDefaultTokenForCharacter(character, graphic)` → `graphic.remove()`.

**NPC token bars must be unlinked.** `bar1_link` to the `hp` attribute makes
every token of that creature share one HP pool — damage one goblin and all four
drop. Set `bar1_value`/`bar1_max` as plain numbers instead.

**`generateRowID()` is not exposed to Mods.** Build IDs with Roll20's own
alphabet (see `LL_Spells.js.tmpl`), 20 chars, underscores mapped to dashes
because attribute names split on `_`. Guard against same-millisecond collisions.

**`createObj('page', ...)` returns null.** Mods cannot create pages. Use
`browser/create-blank-pages.js`, then `!llmaps adopt`.

**Leaving a sheet field blank is not neutral.** An empty `spellschool` makes the
sheet default that dropdown to Abjuration and *save* it. Write the real value or
accept a wrong one.

**The library search caps at ~270 results with no paging.** Broad sweeps will not
reach a large library; fill the rest by exact name.

## Style rules for the mod scripts

- Every failure path reports. A script that returns silently on a null is a bug
  even if the null was expected — three separate silent failures happened here.
- Every destructive pass has a `revert`, with the originals kept in `state`.
- Every batch command has a `test` that does exactly one item, verbosely.
- Re-running must be safe: skip or update in place, never duplicate.
- Batches use `setTimeout` chaining, not loops — the sandbox has a CPU budget.

## Verifying changes

There is no test suite; the target is a live VTT. The discipline that worked:

1. Change the generator, run it, `node --check` the emitted script.
2. `!<cmd> test` on one item and *look at the sheet or page*.
3. Only then run the batch.

For grid work, render the detected grid over the image and look at it. Numbers
that seem plausible are not evidence; three separate detection attempts passed
their own sanity checks and were wrong.

## When something fails silently

Check, in this order: does the handler fire at all (add a `ping`); is `say()`
being handed macro syntax; did a `createObj` return null rather than throw.
Those three account for every silent failure seen so far.
