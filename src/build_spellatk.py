"""Stage 5c: token-action buttons for spells that need an attack roll.

    python src/build_spellatk.py

Emits LL_SpellAtk.js, which gives every NPC spell whose row has
spellattack = Ranged or Melee its own token action. Save-based spells and
healing get nothing - there is no attack roll to make, and the spell card from
stage 5b already carries their detail.

The macro reads @{spell_attack_bonus} off the caster's own sheet, so it stays
correct if the NPC's stats change. It uses the same npcfullatk roll template as
the sheet's weapon actions.

Reads the same casters file as build_spelldata.py ("casters" in config.json).
"""
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from r20.config import CFG, REPO          # noqa: E402
from _tmpl import render_map              # noqa: E402


def main():
    casters_file = CFG.get("casters") or "casters.json"
    if not os.path.isabs(casters_file):
        casters_file = os.path.join(REPO, casters_file)
    if not os.path.exists(casters_file):
        raise SystemExit(
            f"{casters_file}: not found.\n"
            "  cp examples/casters.example.json casters.json   and edit it,\n"
            '  or set "casters" in config.json'
        )
    with open(casters_file, encoding="utf-8") as fh:
        cfg = json.load(fh)

    casters = cfg.get("casters") or []
    if not casters:
        raise SystemExit(f"{casters_file}: no casters listed")

    blob = json.dumps(casters, ensure_ascii=False)
    stamp = cfg.get("version") or hashlib.sha256(blob.encode()).hexdigest()[:7]
    version = "%s (%s)" % (stamp, datetime.date.today().isoformat())

    render_map("LL_SpellAtk.js.tmpl", {
        "VERSION": version,
        "CASTERS": blob,
    }, "LL_SpellAtk.js")
    print(f"build {version} - {len(casters)} caster(s) targeted")
    print("which spells get a button is decided in Roll20 at run time, from each")
    print("row's spellattack field, so run build_spelldata.py first.")


if __name__ == "__main__":
    main()
