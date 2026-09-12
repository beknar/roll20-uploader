# 8. Uploading art and harvesting URLs

Prerequisite for both [art](03-art.md) and [maps](06-maps.md).

## Why this step exists

The Roll20 Mod API refuses any `imgsrc` that is not already hosted by Roll20.
There is no way to point a script at a file on your disk, your web server, or
any CDN. The image must be uploaded to your Roll20 art library first, and the
script must then use the URL Roll20 assigned it.

The API also cannot *read* your library. So the URLs have to come out of the
browser.

## 1. Upload

Sidebar → Art Library → Upload. The file picker is multi-select, so this is a
few batches, not a few hundred clicks.

**Do not rename anything.** Roll20 derives the library name from the filename,
and the filename stem is the key that matches art back to notes and maps.

Upload only what you need:

- one portrait per NPC (`goblin.jpg`)
- one token per NPC at a sensible size (`goblin-token-128.png`) — a 128px token
  is ~35 KB against ~600 KB for a full-size one, and at token scale you cannot
  tell the difference
- the map images you actually intend to use

Roll20 converts uploads to `.webp` and the library name changes accordingly
(`goblin.jpg` → `goblin.webp`). The tooling strips extensions before matching,
so this does not matter.

## 2. Harvest

1. Open the game, let it load, open the **Art Library** tab.
2. DevTools → Console → paste `browser/harvest-art-urls.js`.
3. Run:

```js
await LL.sweep()                 // wide passes
LL.count()                       // how many found
await LL.find(['goblin','ogre']) // fill gaps by exact stem; returns what is still missing
copy(LL.json())                  // clipboard
```

4. Paste into `library.json` next to your config.

### Why it needs both a sweep and fills

The library search caps at roughly **270 results and has no paging**. A large
library cannot be enumerated by one broad term. `sweep()` runs several wide
terms and unions the results; `find()` searches exact stems for whatever is
still missing. Each search takes 3–5 seconds, so exact-name fills for hundreds
of files are slow — the sweep is what makes it practical.

### Verifying coverage

`build_art.py` and `build_maps.py` both report what they could not find. Check
that list before running anything in Roll20 — a missing entry means a silently
skipped character or map, not an error.

## How the matching works

Library name `goblin.webp` → stem `goblin`. A note whose portrait is
`goblin.jpg` looks for stem `goblin` and, for its token, stem
`goblin` + `art.token_suffix` from your config.

If your art is named differently, change `token_suffix` rather than renaming
hundreds of files.
