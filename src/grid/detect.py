"""Grid pitch + phase detection for gridded map plates.

Method: the printed grid is the only periodic structure that spans the whole
image, so project edge energy onto each axis and look for the period that best
explains the resulting 1-D signal. Autocorrelation finds the pitch; a phase
sweep at that pitch finds the offset. Independent per axis, then reconciled --
a real square grid has the same pitch both ways, and disagreement is the
cheapest signal that detection failed.
"""
import sys, numpy as np
from PIL import Image
from scipy.signal import find_peaks

def axis_profile(g, axis):
    # First difference along the axis = vertical (or horizontal) edge energy,
    # summed across the other axis. Grid lines show as evenly spaced spikes.
    d = np.abs(np.diff(g.astype(np.float32), axis=axis))
    p = d.sum(axis=1-axis)
    p = p - p.mean()
    return p / (np.abs(p).max() + 1e-9)

def best_pitch(p, lo=14, hi=200):
    n = len(p)
    ac = np.correlate(p, p, mode='full')[n-1:]
    ac /= (ac[0] + 1e-9)
    hi = min(hi, n//3)
    seg = ac[lo:hi]
    peaks, _ = find_peaks(seg, height=0.05, distance=6)
    if not len(peaks): return None, 0.0, ac
    # Score each candidate by how well its harmonics also line up: a true pitch
    # repeats, a spurious one does not.
    best, bestscore = None, -1
    for pk in peaks:
        t = pk + lo
        hs = [ac[int(round(t*k))] for k in (1,2,3,4) if int(round(t*k)) < len(ac)]
        score = float(np.mean(hs)) * (1 + 0.25*len(hs))
        if score > bestscore: best, bestscore = t, score
    return best, bestscore, ac

def best_phase(p, pitch):
    n = len(p)
    idx = np.arange(n)
    best, bestv = 0, -1e9
    for ph in range(int(pitch)):
        mask = ((idx - ph) % pitch) < 1.5
        v = p[mask].mean() if mask.any() else -1e9
        if v > bestv: best, bestv = ph, v
    return best, float(bestv)

def detect(path):
    im = Image.open(path).convert('L')
    g = np.asarray(im)
    out = {"file": path.split('/')[-1], "size": im.size}
    res = {}
    for name, ax in (("x", 1), ("y", 0)):
        p = axis_profile(g, ax)
        pitch, score, _ = best_pitch(p)
        if pitch is None:
            res[name] = None; continue
        ph, pv = best_phase(p, pitch)
        res[name] = {"pitch": float(pitch), "score": round(score,3),
                     "phase": int(ph), "phase_strength": round(pv,3)}
    out["axes"] = res
    if res.get("x") and res.get("y"):
        px, py = res["x"]["pitch"], res["y"]["pitch"]
        out["agree"] = round(abs(px-py)/max(px,py), 3)
        out["pitch"] = round((px+py)/2, 2)
        out["confident"] = out["agree"] < 0.04 and min(res["x"]["score"], res["y"]["score"]) > 0.12
    else:
        out["confident"] = False
    return out

if __name__ == "__main__":
    import json
    for f in sys.argv[1:]:
        print(json.dumps(detect(f), indent=1))
