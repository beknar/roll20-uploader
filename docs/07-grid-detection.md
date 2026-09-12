# 7. Grid detection

How `src/grid/` decides what a map's printed grid pitch is, what it gets right,
and where it fails. Read this before trusting a number it produces.

## Two independent methods

**`detect.py` — autocorrelation.** The printed grid is usually the only periodic
structure spanning the whole image. Project edge energy onto each axis, then
find the period that best explains the resulting 1-D signal. Candidates are
scored by whether their harmonics also line up, which suppresses the classic
half-pitch error. Run per axis; a real square grid gives the same answer both
ways, and disagreement is the cheapest available signal that detection failed.

**`measure.py` — direct line spacing.** Slide a window over the page, find ruled
lines in each, and take the commonest spacing across all of them. A window over
hatching contributes noise, but noise scatters while the true pitch repeats, so
the mode is the grid.

They share no code. Agreement between them is real evidence; agreement of one
with itself is not.

## The confidence flag

`detect()` reports `confident` only when both axes agree within 4% and both
score above a floor. It is deliberately conservative — it refuses pages it could
have handled. In practice it fired on every page with one real grid and refused
every page without one, at the cost of also refusing some it would have got
right.

`scan_maps.py` cross-checks the two methods and only calls something a `plate`
when they agree within 12%.

## What it cannot do

**Find a grid that is not there.** Obvious in hindsight, and it cost three failed
attempts on a different project: AI-generated location illustrations have no
printed grid at all, so there is nothing to detect and any number produced is
noise. Check the image before debugging the detector.

**Separate maps on a multi-map page.** `region.py` scores blocks by local
periodicity and keeps connected blobs, which finds the main map on a page
cleanly but merges or misses insets — especially where soft, cloudy borders
connect them. Multi-map plates need boxes drawn by hand.

**Phase reliably.** Pitch is the sturdy half. Phase (where the first line falls)
is weaker — expect errors of a few pixels, which become visible drift once the
image is scaled to 70px squares. If you crop a map, crop so the edge lands on a
grid line; phase then becomes zero by construction.

**Hex grids.** `detect.py` measures for squares. A hex map returns nothing
meaningful.

## Verify by looking

The single most useful habit. Render the detected grid over the image and look
at it:

```python
from PIL import Image, ImageDraw
from grid.detect import detect
d = detect(path); p = d["pitch"]
im = Image.open(path).convert("RGB").crop(box)
im = im.resize((im.width*3, im.height*3), Image.LANCZOS)
dr = ImageDraw.Draw(im, "RGBA")
x = 0
while x < im.width:  dr.line([(x,0),(x,im.height)], fill=(255,0,0,180), width=2); x += p*3
y = 0
while y < im.height: dr.line([(0,y),(im.width,y)], fill=(255,0,0,180), width=2); y += p*3
im.save("check.jpg")
```

Crop somewhere with clean floor, not hatching. A plausible-looking number is not
evidence; three separate detection approaches passed their own internal checks
and were wrong.
