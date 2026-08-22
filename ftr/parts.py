"""Component catalogue loader — data/parts.json.

Maps physical components (DPF sensor, PCM, Haldex DEM, ...) to their
location, Ford part numbers, related fault codes and which app function
can test them. Part numbers must always be VIN-verified before ordering.
"""

import json

from . import paths

CFG = paths.REPO_ROOT / "data" / "parts.json"


def load():
    """Return the list of component dicts (empty list if not found)."""
    if not CFG.exists():
        return []
    try:
        return json.loads(CFG.read_text(encoding="utf-8"))["components"]
    except (json.JSONDecodeError, KeyError):
        return []


def for_code(code):
    """Components that list this fault code (e.g. 'P2463')."""
    code = code.upper()
    return [c for c in load()
            if code in [x.upper() for x in c.get("fault_codes", [])]]


def for_symptom(text):
    """Components whose symptom keywords appear in free text."""
    text = text.lower()
    hits = []
    for c in load():
        if any(s in text for s in c.get("symptoms", [])):
            hits.append(c)
    return hits


def describe(c):
    """Human-readable detail block for one component."""
    lines = [c["name"], f"  Location: {c['location']}"]
    if c.get("part_numbers"):
        lines.append("  Ford part no(s): " + ", ".join(c["part_numbers"]))
    if c.get("superseded_by"):
        lines.append("  Superseded by:   " + ", ".join(c["superseded_by"]))
    if c.get("cross_refs"):
        lines.append("  Cross-refs:      " + ", ".join(c["cross_refs"]))
    if c.get("fault_codes"):
        lines.append("  Related codes:   " + ", ".join(c["fault_codes"]))
    if c.get("app_tests"):
        lines.append("  This app can:    " + "; ".join(c["app_tests"]))
    lines.append("  ⚠ Verify part number against your VIN (Ford ETIS) "
                 "before ordering.")
    return "\n".join(lines)
