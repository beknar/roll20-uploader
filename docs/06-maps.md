# 6. Maps

Do [library URLs](08-library-urls.md) first.

```bash
python src/scan_maps.py --sheet   # survey images -> build/maps.manifest.json + contact sheet
#   ... edit the manifest ...
python src/build_maps.py library.json
```

## The manifest step is not optional

`scan_maps.py` writes a *guess*. Open the contact sheet and correct it before
building. The detector is reliable about grid pitch when a printed grid exists,
but it cannot tell a dungeon map from an advertisement — and scanned module PDFs
are full of covers, ad pages and multi-map spreads.

Each entry has a `kind`:

| kind | geometry | when |
|---|---|---|
| `plate` | image scaled so its printed squares hit 70px, grid on | scanned page with a real, measured grid |
| `scene` | page `scene_width_squares` wide, aspect kept, grid off | gridless art — backdrops, location illustrations |
| `manual` | native pixel size, grid on, nothing scaled | a grid exists but the pitch is not trustworthy |

Add `"skip": true` to drop an entry entirely. Covers and adverts belong here.

`manual` is the honest option, not a failure: the image goes in at 1:1 with the
grid on, which is the right starting point for Roll20's **Align to Grid** tool.

## Why scaling, not grid offset

Roll20's grid is fixed at 70px per square and has no offset. You align a map by
scaling and moving the **image** until its printed squares match that grid. So
for a plate:

```
graphic size = image pixels * 70 / printed pitch
```

That is the whole alignment calculation. It is simpler than Foundry's model,
where you move the grid instead — but it means the source image gets upscaled,
sometimes heavily. A 1275px scan with a 16px pitch is blown up 4.4×; tokens stay
crisp, the map goes soft. If you have the source PDF, re-export those plates at
300 dpi and re-upload — only the URLs change.

## Mods cannot create pages

`createObj('page', ...)` returns null. The API can configure pages but not make
them. So:

1. `build_maps.py` tells you how many pages you need.
2. Open the game, DevTools → Console, paste `browser/create-blank-pages.js`:
   ```js
   await makeBlankPages(76)
   ```
   Reload and run `countBlankPages()` to confirm they persisted.
3. In chat:
   ```
   !llmaps adopt
   ```

`adopt` claims pages that are **still named "Untitled" and completely empty** —
no graphics, paths or text. It cannot overwrite a page you have built.

```
!llmaps probe        # test whether createObj('page') works in your game
!llmaps pending      # what still needs a page, and how many blanks are available
!llmaps adopt [n]    # configure up to n blank pages
!llmaps held         # what was deliberately not built, and why
!llmaps status       # how many exist
!llmaps revert       # archive the pages this script created
```

Run `!llmaps probe` first. If Roll20 ever allows page creation from a Mod, it
will tell you and `!llmaps apply` becomes available.

## Notes

- New pages land at the **root** of the Page Toolbar. Adopt renames and
  configures; it does not touch folder organisation.
- `revert` archives rather than deletes — Roll20 does not let a Mod delete a
  page outright.
- Hex maps: set `"gridtype": "hex"` on a `manual` entry.
- `feet_per_square` comes from config. Old-school modules commonly rule at 10ft,
  not 5ft.
