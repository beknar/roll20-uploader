"""Stage 5d: make ATTACK spell rows actually roll.

    python src/build_spelllink.py

Emits LL_SpellLink.js. A spell row with spelloutput = ATTACK still posts a plain
card, because the sheet only builds its linked repeating_attack row when the row
is edited in the sheet UI and the API cannot fire that worker. This builds the
same attack row and points the spell's rollcontent at it, so clicking the spell
rolls it - attack roll or save DC, damage, healing, and the "Cast at what level?"
prompt on upcastable spells.

All of the per-spell values are read off the sheet at run time, so this script
carries no spell data of its own. Run build_spelldata.py first.

Reads the same casters file as build_spelldata.py ("casters" in config.json).
"""
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from r20.config import CFG, REPO          # noqa: E402
from r20.spelldata import upcast_ladders  # noqa: E402
from _tmpl import render_map              # noqa: E402


def main():
    casters_file = CFG.get("casters") or "casters.json"
    if not os.path.isabs(casters_file):
        casters_file = os.path.join(REPO, casters_file)
    if not os.path.exists(casters_file):
        raise SystemExit(f"{casters_file}: not found. See examples/casters.example.json")
    with open(casters_file, encoding="utf-8") as fh:
        cfg = json.load(fh)

    casters = cfg.get("casters") or []
    if not casters:
        raise SystemExit(f"{casters_file}: no casters listed")

    blob = json.dumps(casters, ensure_ascii=False)
    stamp = cfg.get("version") or hashlib.sha256(blob.encode()).hexdigest()[:7]
    version = "%s (%s)" % (stamp, datetime.date.today().isoformat())

    # Spells whose upcast ladder is not "a die per level" need an override, so
    # the level prompt offers the right number of dice. Needs the spell data;
    # without it the mod falls back to per-level for everything.
    ladders = {}
    spell_dir = CFG.get("spell_data")
    if spell_dir and cfg.get("spells"):
        if not os.path.isabs(spell_dir):
            spell_dir = os.path.join(REPO, spell_dir)
        if os.path.isdir(spell_dir):
            ladders = upcast_ladders(cfg["spells"], spell_dir, cfg.get("aliases"))
    if ladders:
        print("non-standard upcast ladders: " +
              ", ".join("%s=%s" % (k, v) for k, v in sorted(ladders.items())))

    render_map("LL_SpellLink.js.tmpl", {
        "VERSION": version,
        "CASTERS": blob,
        "LADDERS": json.dumps(ladders, separators=(",", ":")),
    }, "LL_SpellLink.js")
    print(f"build {version} - {len(casters)} caster(s) targeted")


if __name__ == "__main__":
    main()
