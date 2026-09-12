"""Stage 6a: survey map images and write a manifest you then edit.

    python src/scan_maps.py                  # scan the configured map folders
    python src/scan_maps.py --sheet          # also write a contact sheet jpg
    python src/scan_maps.py /some/other/dir  # scan an arbitrary folder

For each image it records size, the detected grid pitch, and whether detection
was confident. It then guesses a `kind`:

    plate   a scanned page with a printed grid; the image gets scaled so its
            squares land on Roll20's fixed 70px grid
    scene   gridless art; page sized to the image, grid off
    manual  gridded but the pitch is not trustworthy; placed at native size with
            the grid on so you can use Roll20's Align to Grid tool

THE GUESS IS A STARTING POINT, NOT AN ANSWER. Open the contact sheet, look at
what the detector claimed, and edit build/maps.manifest.json before building.
Detection is reliable about pitch when a real grid exists and honest about not
knowing otherwise, but it cannot tell a dungeon map from an advertisement.
"""
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from r20.config import CFG, out_path, attach
from grid.detect import detect
from grid.measure import measure

EXT = ("*.jpg", "*.jpeg", "*.png", "*.webp")

def folders():
    out = []
    for kind in ("maps", "maps_generic", "locations"):
        try:
            p = attach(kind)
        except KeyError:
            continue
        if os.path.isdir(p):
            out.append(p)
    return out

def images(dirs):
    seen, out = set(), []
    for d in dirs:
        for e in EXT:
            for p in sorted(glob.glob(os.path.join(d, e))):
                if os.path.realpath(p) in seen:
                    continue
                seen.add(os.path.realpath(p))
                out.append(p)
    return out

def classify(det, measured):
    """Cross-check autocorrelation against direct line spacing.

    Only two verdicts are ever produced automatically: "plate" when the two
    independent methods agree, and "review" when they do not. Nothing here can
    tell a dungeon map from an advertisement -- both are ink on paper with some
    periodic texture -- so everything else is handed to you rather than guessed.
    """
    p = det.get("pitch")
    real = [v for v, _ in (measured or []) if v >= 14][:1]
    m = float(real[0]) if real else None
    if p and m and det.get("confident") and abs(m - p) / max(m, p) < 0.12:
        return "plate", round(p, 1)
    return "review", (round(m, 1) if m else None)

def contact_sheet(rows, path, thumb_w=300, cols=6):
    from PIL import ImageDraw
    n = len(rows)
    if not n: return
    r0 = Image.open(rows[0]["path"])
    th = int(thumb_w * r0.height / r0.width)
    rws = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w + (cols + 1) * 8,
                              rws * (th + 26) + (rws + 1) * 8), (30, 30, 34))
    dr = ImageDraw.Draw(sheet)
    for i, r in enumerate(rows):
        im = Image.open(r["path"]).convert("RGB").resize((thumb_w, th), Image.LANCZOS)
        c, rr = i % cols, i // cols
        x, y = 8 + c * (thumb_w + 8), 8 + rr * (th + 26)
        sheet.paste(im, (x, y + 22))
        dr.text((x + 2, y + 5), f"{r['slug'][:26]}  {r['kind']}  pitch {r.get('pitch')}",
                fill=(240, 240, 240))
    sheet.save(path, quality=90)
    print("contact sheet ->", path)

def main(argv):
    want_sheet = "--sheet" in argv
    dirs = [a for a in argv[1:] if not a.startswith("--")] or folders()
    if not dirs:
        raise SystemExit("No map folders configured or given. See config.json -> attachments.")
    rows = []
    for p in images(dirs):
        det = detect(p)
        try:
            top, _ = measure(p)
        except Exception:
            top = None
        kind, pitch = classify(det, top)
        w, h = Image.open(p).size
        slug = os.path.splitext(os.path.basename(p))[0]
        row = {"slug": slug, "name": slug.replace("-", " ").title(),
               "path": p, "w": w, "h": h, "kind": kind,
               "detected": det.get("pitch"), "measured": pitch,
               "confident": bool(det.get("confident"))}
        if kind == "plate":
            row["pitch"] = pitch
        else:
            row["note"] = ("SET kind TO scene / plate / manual, or skip:true. "
                           f"autocorrelation {det.get('pitch')}, line spacing {pitch}")
        rows.append(row)
        print(f"{slug:<34}{kind:<8}auto {str(det.get('pitch')):>6}  "
              f"lines {str(pitch):>6}  {'OK' if det.get('confident') else '?'}   {w}x{h}")
    path = out_path("maps.manifest.json")
    json.dump(rows, open(path, "w", encoding="utf-8"), indent=1)
    print(f"\n{len(rows)} images -> {path}")
    n_rev = sum(1 for r in rows if r["kind"] == "review")
    print(f"{n_rev} need a decision. EDIT THAT FILE before build_maps.py:")
    print("  kind=scene   gridless art (no alignment needed)")
    print("  kind=plate   printed grid -- also set \"pitch\"")
    print("  kind=manual  grid present but pitch unsettled; goes in at 1:1 to align by hand")
    print("  skip=true    not a map at all (covers, adverts, text pages)")
    if want_sheet:
        contact_sheet(rows, out_path("maps.contact-sheet.jpg"))

if __name__ == "__main__":
    main(sys.argv)
