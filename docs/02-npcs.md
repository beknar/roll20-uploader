# 2. NPCs

Builds a character sheet per NPC: abilities, AC, HP, saves, skills, senses,
resistances, traits, actions, reactions, legendary actions.

```bash
python src/extract_npcs.py     # vault -> build/npcs.json
python src/build_npcs.py       # -> build/LL_Payload_*.js + build/LL_Importer.js
```

`extract_npcs.py` prints what it found, including which notes had no stat block
and which were resolved from an SRD base. Read that output — it is the cheapest
place to catch a mis-parsed vault.

## The guard edit

`5e_NPC_JSON_Importer.js` begins its chat handler with:

```js
if (msg.playerid === 'API') return;
```

which means a Mod cannot talk to it at all — messages from scripts are ignored by
design. Change that line to:

```js
if (msg.playerid === 'API' && msg.who !== 'LL-DRIVER') return;   // allow our driver
```

Without this the driver has no way to hand NPCs over and the run does nothing.

## Installing

Paste into Settings → Mods, as separate scripts:

- `LL_Payload_1.js` … `LL_Payload_N.js` — the data, split so no one script is enormous
- `LL_Importer.js` — the driver

Save once, after all of them are in. Each save restarts the sandbox.

## Running

```
!llimport test          # one NPC, verbosely
!llimport start         # the queue
!llimport status        # progress
!llimport pause         # stop; start resumes
!llimport retry         # re-run whatever failed
```

Roughly 20 seconds per NPC by default (`!llimport delay <seconds>` to change).
Progress lives in `state`, so a sandbox restart does not lose it.

`start` skips any NPC whose character already exists, so it is safe to re-run.
`!llimport start force` overrides that.

### Check before committing to the batch

After `!llimport test`, open the sheet and confirm:

- AC, HP and the HP formula
- attack rolls: to-hit and damage on one melee action
- passive traits are in **Traits**, not **Actions**
- a description-only action (Multiattack) has no attack roll

If the attack numbers are right for one creature, the parser is working; the
same code produced every other one.

## How delivery works

Worth knowing when it misbehaves. The driver cannot simply `sendChat` the NPC
JSON — Roll20's chat parser tries to resolve `@{...}` and `[[...]]` inside the
payload and throws. Instead:

1. The NPC JSON is written to a scratch handout (`LL-IMPORT`).
2. A short command naming that handout is sent as `LL-DRIVER`.
3. The importer reads the handout.

That is why the guard edit matters, and why the handout must not be deleted
mid-run. Handout notes are rich text, so the payload is stripped to plain text
first — HTML in the JSON gets parsed by Roll20 and destroys the JSON.

## Troubleshooting

**No output at all from `!llimport test`.** The importer whispers its result to
whoever sent the command; `LL-DRIVER` is not a real player, so that whisper goes
nowhere. Look for the sheet, not the message.

**"No such handout".** `LL-IMPORT` was deleted. It is recreated on the next
delivery; just re-run.

**Duplicate sheets.** `start` was run with `force`, or the payload contains the
same NPC twice. `build_npcs.py` reports its chunk contents — check for overlap.
