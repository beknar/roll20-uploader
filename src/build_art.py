"""Stage 3: portraits and default tokens.

    python src/build_art.py library.json

`library.json` is the name -> URL map you harvest from your Roll20 art library
(see browser/harvest-art-urls.js and docs/08-library-urls.md). The Roll20 Mod API
refuses any image that is not already hosted by Roll20, so there is no way round
uploading first and harvesting the URLs.

Matching is by filename stem: a note whose portrait is `goblin.jpg` looks for a
library entry called `goblin` (any extension -- Roll20 converts uploads to webp).
Token art is the same stem plus the configured token suffix.

Emits LL_Art.js.
"""
import json, os, re, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r20.config import CFG, out_path, vault_path
from r20 import vault as V
from _tmpl import render

BASE = "https://files.d20.io/images/"
SIZE_PX = {"Tiny": 70, "Small": 70, "Medium": 70,
           "Large": 140, "Huge": 210, "Gargantuan": 280}

def strip_ext(n):
    return re.sub(r"\.(webp|png|jpe?g|gif)$", "", str(n), flags=re.I)

def key_of(url):
    """files.d20.io/images/<id>/<hash>/max.webp -> '<id>/<hash>'"""
    u = str(url).split("?")[0]
    if not u.startswith(BASE):
        return None
    return re.sub(r"/\w+\.\w+$", "", u[len(BASE):])

def portrait_stem_for(note_frontmatter):
    """Vault notes point at their own art; we only need the file's stem."""
    for field in ("portrait", "image", "img"):
        v = note_frontmatter.get(field)
        if v:
            return strip_ext(os.path.basename(str(v).replace("\\", "/")))
    return None

def main(library_json):
    lib = {strip_ext(k).lower(): v for k, v in json.load(open(library_json, encoding="utf-8")).items()}
    npcs = {n["name"]: n for n in json.load(open(out_path("npcs.json"), encoding="utf-8"))}

    rows, missing = [], []
    for path, fm, body in V.iter_notes():
        name = fm.get("name") or os.path.splitext(os.path.basename(path))[0]
        if name not in npcs:
            continue
        stem = portrait_stem_for(fm)
        if not stem:
            missing.append((name, "no portrait field in the note"))
            continue
        p_url = lib.get(stem.lower())
        t_url = lib.get((stem + CFG["art"]["token_suffix"]).lower())
        if not p_url or not t_url:
            missing.append((name, f"not in the library: {stem}"
                                  f"{'' if p_url else ' (portrait)'}"
                                  f"{'' if t_url else ' (token)'}"))
            continue
        pk, tk = key_of(p_url), key_of(t_url)
        if not pk or not tk:
            missing.append((name, "url is not a files.d20.io image"))
            continue
        px = SIZE_PX.get(npcs[name].get("size", "Medium"), 70)
        rows.append(json.dumps([name, pk, tk, px], separators=(",", ":")))

    render("LL_Art.js.tmpl", rows, "LL_Art.js")
    if missing:
        print(f"\n{len(missing)} without art:")
        for n, why in missing[:40]:
            print(f"    {n:<32} {why}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
