"""Known-issues knowledge base: multi-vehicle loading + symptom matching.

KBs live as one JSON file per vehicle in data/known_issues/<vehicle>.json —
that is the scaling unit. A new make/model is a new data file, not new code.
"""

import json
import re
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent / "data" / "known_issues"


def available_vehicles():
    """Return {vehicle_key: vehicle_title} for every installed KB."""
    out = {}
    for p in sorted(KB_DIR.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                out[p.stem] = json.load(f).get("vehicle", p.stem)
        except (json.JSONDecodeError, OSError):
            continue
    return out


def load_kb(vehicle=None):
    """Load one KB by key (e.g. 'kuga_mk2'); default = first available."""
    vehicles = available_vehicles()
    if not vehicles:
        raise FileNotFoundError(f"No knowledge bases found in {KB_DIR}")
    key = vehicle or next(iter(vehicles))
    if key not in vehicles:
        raise FileNotFoundError(f"Unknown vehicle '{key}'. Available: {list(vehicles)}")
    with open(KB_DIR / f"{key}.json", encoding="utf-8") as f:
        return json.load(f)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def match(kb, dtcs=(), symptom_text=""):
    """Rank KB issues against observed DTCs and free-text symptoms.

    Scoring: 3 points per DTC hit, 1 per symptom-keyword hit.
    Returns list of (score, issue, dtc_hits, symptom_hits), best first.
    """
    text = _norm(symptom_text)
    dtc_set = {d.upper() for d in dtcs}
    scored = []
    for issue in kb["issues"]:
        score = 0
        dtc_hits = [d for d in issue.get("dtcs", []) if d.upper() in dtc_set]
        score += 3 * len(dtc_hits)
        sym_hits = []
        for phrase in issue.get("symptoms", []):
            p = _norm(phrase)
            if p and all(word in text for word in p.split()):
                sym_hits.append(phrase)
        score += len(sym_hits)
        if score:
            scored.append((score, issue, dtc_hits, sym_hits))
    scored.sort(key=lambda x: -x[0])
    return scored


def render(score, issue, dtc_hits, sym_hits):
    lines = [
        f"[{issue['known_issue'].upper()} known issue | confidence: {issue['confidence']}] {issue['title']}",
    ]
    if dtc_hits:
        lines.append(f"  matching codes: {', '.join(dtc_hits)}")
    if sym_hits:
        lines.append(f"  matching symptoms: {', '.join(sym_hits)}")
    lines.append("  likely causes (most common first):")
    lines += [f"    - {c}" for c in issue["likely_causes"]]
    lines.append("  checks:")
    lines += [f"    - {c}" for c in issue["checks"]]
    if issue.get("sources"):
        lines.append("  sources:")
        lines += [f"    - {s}" for s in issue["sources"]]
    return "\n".join(lines)
