# 3. Portraits and default tokens

Do [library URLs](08-library-urls.md) first.

```bash
python src/build_art.py library.json    # -> build/LL_Art.js
```

Paste into Mods, then:

```
!llart test          # one character, verbosely, then reads back what was stored
!llart apply         # all of them
!llart status        # how many have an avatar
!llart probe [name]  # read back what Roll20 actually stored for a default token
```

## What it sets

- **avatar** — the portrait, at full size
- **default token** — the token art, sized by creature size (Medium 1×1, Large
  2×2, Huge 3×3, Gargantuan 4×4), with a nameplate visible to the GM and hidden
  from players
- **bar1** — max HP as plain numbers

## Two things that are not obvious

**`character.set('defaulttoken', json)` does not work.** It does not throw. It
simply fails to register a token, and Roll20 silently falls back to the avatar
image at 1×1 with no bars — which looks like "the token art didn't apply". The
working route, which this script uses, is: create a graphic off-canvas, hand it
to `setDefaultTokenForCharacter()`, delete the graphic.

**Token bars must be unlinked.** Linking `bar1` to the sheet's `hp` attribute
makes every token of that creature share one HP pool — damage one goblin and all
four drop together. `!llart probe` reports `bar1_link empty (correct)` when this
is right.

## Default tokens are not retroactive

A default token only affects tokens dragged out *after* it is set. Tokens
already on a map keep whatever they had. When testing, delete the old token and
drag a fresh one — otherwise you are looking at the previous state and will
conclude the fix failed.

## Housekeeping

The script parks a temporary graphic at (−2000, −2000) on your player page while
registering each token, then deletes it. If a delete ever fails you get
leftovers stacked off the top-left corner of that page. Worth a look after a
large run; they are disposable.
