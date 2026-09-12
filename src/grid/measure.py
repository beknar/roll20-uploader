"""Measure the printed grid pitch directly, by finding ruled lines and taking
the commonest spacing. Independent of the autocorrelation detector, so it is a
real check rather than the same computation twice.

Samples many windows across the page instead of one hand-picked room: a window
over hatching or text contributes noise, but noise is scattered while the true
pitch repeats, so the mode across all windows is the grid.
"""
import numpy as np
from PIL import Image
from collections import Counter

def line_gaps(prof, k=0.8):
    prof = prof.max() - prof
    prof = prof - prof.min()
    if prof.max() < 1e-6: return []
    th = prof.mean() + k * prof.std()
    idx = [i for i in range(1, len(prof)-1)
           if prof[i] > th and prof[i] >= prof[i-1] and prof[i] >= prof[i+1]]
    m = []
    for i in idx:
        if m and i - m[-1][-1] <= 2: m[-1].append(i)
        else: m.append([i])
    c = [float(np.mean(x)) for x in m]
    return [round(v) for v in np.diff(c) if 8 <= v <= 200]

def measure(path, win=180, step=90):
    g = np.asarray(Image.open(path).convert('L')).astype(float)
    H, W = g.shape
    gaps = Counter()
    for y in range(0, H-win, step):
        for x in range(0, W-win, step):
            b = g[y:y+win, x:x+win]
            if b.std() < 6: continue                 # blank paper
            for v in line_gaps(b.mean(axis=0)): gaps[v] += 1
            for v in line_gaps(b.mean(axis=1)): gaps[v] += 1
    if not gaps: return None, gaps
    # Fold near-duplicates (16/17 are the same ruling at jpeg resolution).
    merged = Counter()
    for v, n in gaps.items():
        merged[v] += n
        merged[v-1] += n*0.5; merged[v+1] += n*0.5
    top = merged.most_common(8)
    return top, gaps

if __name__ == "__main__":
    import sys
    M = ""   # set on the command line
    for f in sys.argv[1:]:
        top,_ = measure(M+f)
        print(f, "->", [(int(v), round(n)) for v,n in top])
