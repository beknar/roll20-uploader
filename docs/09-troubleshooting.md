# 9. Troubleshooting

## A command produces no output at all

This is the most common failure and it has three causes. Check them in order.

**1. The handler is not firing.** Add a `ping` case to the script and try it. If
`ping` is also silent, the script did not load or another Mod is throwing during
chat dispatch.

**2. `say()` was handed macro syntax.** Any string containing `@{...}`,
`[[...]]` or `{{...}}` crashes Roll20's chat parser and kills the handler
mid-run with nothing printed. Every script here defangs those before sending —
if you add output, use the existing `say()` helper rather than `sendChat`
directly.

**3. A `createObj` returned null rather than throwing.** Null is not an
exception, so a `try/catch` will not see it. `createObj('page', ...)` always
returns null; `createObj('graphic', ...)` returns null when Roll20 rejects the
`imgsrc`.

## "No ability was found for %{...|repeating_npcaction_rollbase}"

Token actions have not been repaired. Run `!llfix apply` — see
[04-token-actions.md](04-token-actions.md).

## Every token action rolls the same attack

Same cause. The macro resolved but without row context, so all the row-relative
references fell through to the character's globals. `!llfix apply`.

## Token art did not apply — 1×1 token, no bars

The default token was never registered and Roll20 fell back to the avatar. Note
that default tokens are **not retroactive**: delete the existing token and drag a
fresh one before concluding anything. If a fresh token is still wrong, run
`!llart probe <name>` to see what is actually stored.

## Damaging one monster damages all of them

`bar1_link` is set. NPC bars must be unlinked plain numbers. Re-run `!llart
apply` with a current build, then re-drag tokens — existing tokens keep the old
linkage forever.

## A graphic silently fails to appear

`createObj('graphic', ...)` returned null, which almost always means the
`imgsrc` was rejected. It must be a `files.d20.io` URL from **your own** library.
Check that the URL in the generated script matches something in `library.json`,
and that the file is still in your library.

## Spells all filed as Abjuration

The school field was left blank and the sheet defaulted the dropdown — then
saved it. Add the missing spells to `src/r20/data/spell_schools.json`, rebuild,
and re-run `!llspells apply` (it updates rows in place).

## The library harvest is missing files

The search caps at ~270 results with no paging. Run `LL.find([...])` with the
exact stems that are missing. If a stem genuinely is not there, the upload did
not complete — check the Art Library sidebar directly.

## Map grid does not line up

If the map came in as `plate`, the detected pitch was wrong. Change that entry
to `"kind": "manual"` in the manifest, rebuild, re-adopt, and use Roll20's Align
to Grid tool. See [07-grid-detection.md](07-grid-detection.md) for why detection
fails on some pages.

## `!llmaps adopt` says no blank pages found

Blank means *named "Untitled" and completely empty*. A page with anything on it,
or that has been renamed, is deliberately ignored so the script cannot overwrite
your work. Make more with `browser/create-blank-pages.js`.

## The sandbox restarts mid-run

Any save on the Mods page restarts it. Long runs (`!llimport start`,
`!llart apply`) keep progress in `state` and can be resumed, but the in-flight
batch is lost. Stay off that page while a batch is running.

## Everything worked but the sheets look wrong

Check the sheet is **D&D 5e by Roll20** (legacy). The attribute and repeating
section names this project writes are that sheet's; another sheet will accept
the writes and display nothing useful.
