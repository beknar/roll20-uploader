"""Vault access: front-matter notes, slugs, markdown -> HTML.

Paths come from config.json (see r20.config); nothing here is campaign-specific.
"""
import os, re, json, hashlib, unicodedata, yaml, glob
import markdown as md

from .config import CFG

VAULT = CFG["vault"]
ASSET = ""          # only used by the Foundry exporter; kept so token_for() still works

def configure(vault, asset_subdir=""):
    """Override the configured vault at runtime (tests, multiple vaults)."""
    global VAULT, ASSET
    VAULT = vault
    ASSET = asset_subdir

B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
def fid(*parts):
    h = hashlib.sha1("::".join(str(p) for p in parts).encode()).digest()
    n = int.from_bytes(h, "big"); out = ""
    for _ in range(16):
        out += B62[n % 62]; n //= 62
    return out

def slug(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def load_note(path):
    t = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", t, re.S)
    if not m: return {}, t
    try: fm = yaml.safe_load(m.group(1)) or {}
    except Exception: fm = {}
    return fm, m.group(2)

def section(body, title):
    m = re.search(r"^##+\s+" + re.escape(title) + r"\s*$(.*?)(?=^##\s|\Z)", body, re.S | re.M)
    return m.group(1).strip() if m else ""

def drop_sections(body, titles):
    out = body
    for t in titles:
        out = re.sub(r"^##\s+" + re.escape(t) + r"\s*$.*?(?=^##\s|\Z)", "", out, flags=re.S | re.M)
    return out

# ---------- asset path rewriting ----------
def asset_url(rel_or_path):
    """Vault-relative attachment path -> module asset URL."""
    if not rel_or_path: return None
    p = str(rel_or_path).replace("\\", "/")
    m = re.search(r"_attachments/(.+)$", p)
    if not m: return None
    return f"{ASSET}/{m.group(1)}"

def token_for(portrait_url, explicit=None):
    """Use the note's own `token:` field when present, else the -token suffix convention."""
    if explicit:
        u = asset_url(explicit)
        if u: return u
    if not portrait_url: return None
    base, ext = re.match(r"^(.*?)(\.[A-Za-z]+)?$", portrait_url).groups()
    for cand in (base + "-token" + (ext or ""), base + "-token.png"):
        return cand

# ---------- markdown -> HTML ----------
CALLOUT = re.compile(r"^> \[!(\w+)\]([+-]?)\s*(.*)$", re.M)

def preprocess(body, registry=None, self_name=None):
    b = body
    # Obsidian callouts -> blockquote with a lead-in
    def cal(m):
        return f"> **{m.group(3) or m.group(1).title()}**"
    b = CALLOUT.sub(cal, b)
    # images -> module assets
    def img(m):
        alt, src = m.group(1), m.group(2)
        u = asset_url(src)
        return f'<img src="{u}" alt="{alt}" style="max-width:100%;border:none;"/>' if u else ""
    b = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", img, b)
    # wiki links -> @UUID when known, else bold
    def wl(m):
        target, label = m.group(1), m.group(2) or m.group(1)
        if registry:
            hit = registry.get(slug(target))
            if hit and hit["name"] != self_name:
                return f'@UUID[{hit["uuid"]}]{{{label}}}'
        return f"**{label}**"
    b = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", wl, b)
    return b

MDX = ["tables", "sane_lists", "attr_list", "md_in_html"]
def to_html(body, registry=None, self_name=None):
    if not body or not body.strip(): return ""
    b = preprocess(body, registry, self_name)
    html = md.markdown(b, extensions=MDX)
    return html

def iter_notes(subdir=None, pattern="*.md", skip_underscore=True):
    """Yield (path, frontmatter, body). subdir=None walks the whole vault."""
    if subdir is None:
        paths = sorted(glob.glob(os.path.join(VAULT, "**", pattern), recursive=True))
    else:
        paths = sorted(glob.glob(os.path.join(VAULT, subdir, pattern)))
    for p in paths:
        base = os.path.basename(p)
        if skip_underscore and base.startswith("_"): continue
        fm, body = load_note(p)
        yield p, fm, body

STATS = {"coreVersion": "14.367", "systemId": "dnd5e", "systemVersion": "5.3.3"}
