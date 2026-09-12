"""Stage 6b: turn the edited manifest into LL_Maps.js.

    python src/build_maps.py library.json

Needs two inputs:
    build/maps.manifest.json   from scan_maps.py, AFTER you have corrected it
    library.json               name -> URL, harvested from your Roll20 art library

Geometry, by kind:
    plate   graphic = image px * 70 / pitch, page sized to fit, grid on.
            This is the whole alignment trick: Roll20's grid is fixed at 70px and
            has no offset, so you align by scaling the image rather than the grid.
    scene   page `scene_width_squares` wide, aspect kept, grid off.
    manual  native pixel size, grid on, nothing scaled -- a clean starting point
            for Roll20's Align to Grid tool.

Note the Mod API cannot create pages. LL_Maps adopts blank ones you make first;
see docs/06-maps.md.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r20.config import CFG, out_path
from _tmpl import render

BASE = "https://files.d20.io/images/"

def strip_ext(n):
    return re.sub(r"\.(webp|png|jpe?g|gif)$", "", str(n), flags=re.I)

def key_of(url):
    u = str(url).split("?")[0]
    return re.sub(r"/\w+\.\w+$", "", u[len(BASE):]) if u.startswith(BASE) else None

def main(library_json):
    manifest = json.load(open(out_path("maps.manifest.json"), encoding="utf-8"))
    lib = {strip_ext(k).lower(): v for k, v in json.load(open(library_json, encoding="utf-8")).items()}

    rows, missing, skipped, review = [], [], [], []
    for m in manifest:
        if m.get("skip"):
            skipped.append(m["slug"]); continue
        if m["kind"] == "review":
            review.append(m["slug"]); continue
        url = lib.get(strip_ext(m["slug"]).lower())
        if not url:
            missing.append(m["slug"]); continue
        k = key_of(url)
        if not k:
            missing.append(m["slug"] + " (url not a files.d20.io image)"); continue
        row = {"slug": m["slug"], "name": m.get("name") or m["slug"],
               "key": k, "w": m["w"], "h": m["h"], "kind": m["kind"]}
        if m["kind"] == "plate":
            if not m.get("pitch"):
                missing.append(m["slug"] + " (kind=plate but no pitch)"); continue
            row["pitch"] = m["pitch"]
        if m["kind"] == "manual":
            row["gridtype"] = m.get("gridtype", "square")
        rows.append(json.dumps(row, separators=(",", ":")))

    js = render("LL_Maps.js.tmpl", rows, "LL_Maps.js")
    # the template carries the campaign's feet-per-square as a constant
    s = open(js, encoding="utf-8").read()
    s = re.sub(r"var FEET_PER_SQUARE = \d+;",
               f"var FEET_PER_SQUARE = {int(CFG['maps']['feet_per_square'])};", s)
    s = re.sub(r"var targetW = \d+ \* SQ;",
               f"var targetW = {int(CFG['maps']['scene_width_squares'])} * SQ;", s)
    open(js, "w", encoding="utf-8").write(s)

    kinds = {}
    for r in rows:
        d = json.loads(r); kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    print("  by kind:", ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
    print(f"  you will need {len(rows)} blank pages in Roll20 (see docs/06-maps.md)")
    if skipped:
        print(f"  skipped by manifest: {len(skipped)}")
    if review:
        print(f"\n{len(review)} still marked kind=review and were NOT built.")
        print("   Set each to scene / plate / manual (or skip:true) in the manifest.")
        for s_ in review[:40]:
            print("   ", s_)
    if missing:
        print(f"\n{len(missing)} not found in the library:")
        for s_ in missing[:40]:
            print("   ", s_)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
