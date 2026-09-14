"""Fill a mod template. Templates live in mods/templates and carry two markers:
@@DATA@@ for the generated array and @@LABEL@@ for the chat sender name."""
import os
from r20.config import CFG, REPO, out_path

def render(template, rows, out_name):
    src = open(os.path.join(REPO, "mods", "templates", template), encoding="utf-8").read()
    body = ",\n".join(rows)
    js = src.replace("@@DATA@@", body).replace("@@LABEL@@", CFG["campaign_label"])
    path = out_path(out_name)
    open(path, "w", encoding="utf-8").write(js)
    print(f"{out_name}: {len(rows)} entries, {len(js)/1024:.0f} KB -> {path}")
    return path


def render_map(template, mapping, out_name):
    """Fill a template that carries several @@MARKER@@ slots rather than one @@DATA@@.

    mapping is {"MARKER": "already-serialised text"}. @@LABEL@@ is filled from the
    config as usual, so callers do not have to pass it.
    """
    src = open(os.path.join(REPO, "mods", "templates", template), encoding="utf-8").read()
    js = src.replace("@@LABEL@@", CFG["campaign_label"])
    for key, value in mapping.items():
        js = js.replace(f"@@{key}@@", value)
    left = [m for m in ("@@DATA@@", "@@CASTERS@@", "@@INNATE@@", "@@FIELDS@@", "@@VERSION@@") if m in js]
    if left:
        raise SystemExit(f"{template}: unfilled marker(s) {', '.join(left)}")
    path = out_path(out_name)
    open(path, "w", encoding="utf-8").write(js)
    print(f"{out_name}: {len(js)/1024:.0f} KB -> {path}")
    return path
