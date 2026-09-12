"""Configuration. Every path the pipeline touches comes from here.

Resolution order:
    1. $R20_CONFIG                    -- explicit path to a json file
    2. ./config.json                  -- next to wherever you invoked python
    3. <repo root>/config.json

Copy config.example.json to config.json and edit it. config.json is gitignored,
so your local paths never end up in a commit.
"""
import json, os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

DEFAULTS = {
    "vault": None,
    "out": "build",
    "campaign_label": "Campaign",
    "attachments": {
        "creatures": "_attachments/creatures",
        "characters": "_attachments/characters",
        "locations": "_attachments/locations",
        "maps": "_attachments/maps",
        "maps_generic": "_attachments/maps/generic",
    },
    "art": {
        "portrait_suffix": "",        # <slug>.jpg
        "token_suffix": "-token-128", # <slug>-token-128.png  (the small one)
    },
    "maps": {
        "feet_per_square": 10,
        "scene_width_squares": 25,    # how wide a gridless scene page should be
    },
    "srd_actors": None,               # optional: dnd5e/packs/_source/monsters
}

def _deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _deep_merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out

def _find():
    env = os.environ.get("R20_CONFIG")
    if env:
        return Path(env)
    for p in (Path.cwd() / "config.json", REPO / "config.json"):
        if p.exists():
            return p
    return None

def load():
    p = _find()
    if p is None:
        raise SystemExit(
            "No config.json found.\n"
            "  cp config.example.json config.json   and set 'vault' to your vault path,\n"
            "  or set R20_CONFIG=/path/to/config.json"
        )
    cfg = _deep_merge(DEFAULTS, json.loads(p.read_text(encoding="utf-8")))
    if not cfg.get("vault"):
        raise SystemExit(f"{p}: 'vault' is not set.")
    cfg["_path"] = str(p)
    return cfg

CFG = load()

def vault_path(*parts):
    return os.path.join(CFG["vault"], *parts)

def attach(kind, *parts):
    """attach('creatures', 'goblin.jpg') -> <vault>/_attachments/creatures/goblin.jpg"""
    sub = CFG["attachments"][kind]
    return os.path.join(CFG["vault"], sub, *parts)

def out_path(*parts):
    d = CFG["out"]
    if not os.path.isabs(d):
        d = os.path.join(REPO, d)
    full = os.path.join(d, *parts)
    os.makedirs(os.path.dirname(full) or full, exist_ok=True)
    return full
