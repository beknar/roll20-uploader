"""Find the gridded map region(s) on a scanned book plate.

A book page mixes several kinds of ink: body text, a key panel, a compass rose,
hatching, and the map itself. Only the map carries a long-range periodic ruling,
so score every block by how well its local edge profile matches a comb at the
detected pitch, then keep the connected blobs of high score. Multi-map pages
fall out of this naturally as several blobs.
"""
import numpy as np
from PIL import Image
from scipy import ndimage
from .detect import detect, axis_profile

def comb_score(prof, pitch):
    """How periodic is this 1-D edge profile at `pitch`? 0..1-ish."""
    n = len(prof)
    if n < pitch * 3: return 0.0
    p = prof - prof.mean()
    s = np.abs(p).max()
    if s < 1e-6: return 0.0
    p = p / s
    best = 0.0
    for ph in range(int(pitch)):
        idx = np.arange(ph, n, pitch).astype(int)
        if len(idx) < 3: continue
        on = p[idx].mean()
        off = p.mean()
        best = max(best, on - off)
    return float(best)

def gridness(g, pitch, block=None):
    block = block or int(pitch * 4)
    step = block // 2
    H, W = g.shape
    ys = range(0, max(1, H - block + 1), step)
    xs = range(0, max(1, W - block + 1), step)
    m = np.zeros((len(list(ys)), len(list(xs))), dtype=np.float32)
    for j, y in enumerate(range(0, max(1, H - block + 1), step)):
        for i, x in enumerate(range(0, max(1, W - block + 1), step)):
            b = g[y:y+block, x:x+block].astype(np.float32)
            sx = comb_score(np.abs(np.diff(b, axis=1)).sum(axis=0), pitch)
            sy = comb_score(np.abs(np.diff(b, axis=0)).sum(axis=1), pitch)
            m[j, i] = min(sx, sy)          # a grid needs BOTH axes
    return m, block, step

def regions(path, min_squares=6):
    d = detect(path)
    pitch = d.get("pitch")
    im = Image.open(path).convert('L')
    g = np.asarray(im)
    out = {"file": path.split('/')[-1], "size": im.size, "pitch": pitch,
           "confident": d.get("confident"), "boxes": []}
    if not pitch or pitch < 8:
        return out
    m, block, step = gridness(g, pitch)
    if m.size == 0: return out
    thr = max(0.12, float(np.percentile(m, 75)))
    mask = m > thr
    mask = ndimage.binary_closing(mask, np.ones((3, 3)))
    mask = ndimage.binary_opening(mask, np.ones((2, 2)))
    lab, n = ndimage.label(mask)
    for k in range(1, n + 1):
        ys, xs = np.where(lab == k)
        if len(ys) < 4: continue
        y0 = ys.min() * step; y1 = ys.max() * step + block
        x0 = xs.min() * step; x1 = xs.max() * step + block
        w_sq = (x1 - x0) / pitch; h_sq = (y1 - y0) / pitch
        if w_sq < min_squares or h_sq < min_squares: continue
        out["boxes"].append({"box": [int(x0), int(y0), int(min(x1, im.width)), int(min(y1, im.height))],
                             "squares": [round(w_sq, 1), round(h_sq, 1)],
                             "blocks": int(len(ys)),
                             "mean_score": round(float(m[ys, xs].mean()), 3)})
    out["boxes"].sort(key=lambda b: -(b["box"][2]-b["box"][0])*(b["box"][3]-b["box"][1]))
    return out

if __name__ == "__main__":
    import sys, json
    for f in sys.argv[1:]:
        print(json.dumps(regions(f), indent=1))
