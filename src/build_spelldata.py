"""Stage 5b: fill in the *detail* on spell rows that already exist.

    python src/build_spelldata.py

`build_spells.py` files each caster's spells under the right level and sets slot
totals, but leaves every row blank past its name. This stage fills the rest:
description, ritual flag, casting time, range, components, concentration,
duration, casting ability, the innate marker, and the roll fields (output,
attack, damage and type, healing, ability-mod, cantrip progression).

Spell text comes from a local 5etools dataset -- point "spell_data" in
config.json at any copy of its `data/spells/` directory (a self-hosted mirror, or
a checkout of the 5etools source repo). Nothing is invented: a spell with no
match in the dataset is reported and left alone.

Which casters to touch, and which spells to bake into the payload, come from the
file named by "casters" in config.json. See examples/casters.example.json.
"""
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from r20.config import CFG, REPO, out_path          # noqa: E402
from r20.spelldata import FIELDS, build_table       # noqa: E402
from _tmpl import render_map                        # noqa: E402


def _resolve(path):
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def main():
    spell_dir = CFG.get("spell_data")
    if not spell_dir:
        raise SystemExit(
            'config.json: "spell_data" is not set.\n'
            "  Point it at a 5etools data/spells directory, e.g.\n"
            '    "spell_data": "/path/to/5etools/data/spells"'
        )
    spell_dir = _resolve(spell_dir)
    if not os.path.isdir(spell_dir):
        raise SystemExit(f"{spell_dir}: not a directory")

    casters_file = _resolve(CFG.get("casters") or "casters.json")
    if not os.path.exists(casters_file):
        raise SystemExit(
            f"{casters_file}: not found.\n"
            "  cp examples/casters.example.json casters.json   and edit it,\n"
            '  or set "casters" in config.json'
        )
    with open(casters_file, encoding="utf-8") as fh:
        cfg = json.load(fh)

    casters = cfg.get("casters") or []
    innate = cfg.get("innate") or []
    names = cfg.get("spells") or []
    if not casters:
        raise SystemExit(f"{casters_file}: no casters listed")
    if not names:
        raise SystemExit(f"{casters_file}: no spells listed")

    table, missing = build_table(names, spell_dir, cfg.get("aliases"))
    for name in missing:
        print(f"  no dataset match, skipped: {name}", file=sys.stderr)

    payload = json.dumps(table, separators=(",", ":"), ensure_ascii=False)

    # Stamp the build so a downloaded file can be told apart from an earlier one,
    # and so !llspelldata ping can report which build Roll20 actually has loaded.
    # An explicit "version" in casters.json wins; otherwise use a content hash.
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:7]
    stamp = cfg.get("version") or digest
    version = "%s (%s, %d spells)" % (
        stamp, datetime.date.today().isoformat(), len(table))

    render_map("LL_SpellData.js.tmpl", {
        "VERSION": version,
        "CASTERS": json.dumps(casters, ensure_ascii=False),
        "INNATE": json.dumps(innate, ensure_ascii=False),
        "FIELDS": json.dumps(FIELDS),
        "DATA": payload,
    }, "LL_SpellData.js")

    print(f"build {version}")
    print(f"{len(table)} spell(s) baked in, {len(casters)} caster(s) targeted"
          + (f", {len(missing)} unmatched" if missing else ""))


if __name__ == "__main__":
    main()
