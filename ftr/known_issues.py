"""Known-issues knowledge base: load, match by DTCs and symptom text."""

import json
import re
from pathlib import Path

DEFAULT_KB = Path(__file__).resolve().parent.parent / "data" / "known_issues_kuga_mk2.json"


def load_kb(path=None):
    with open(path or DEFAULT_KB, encoding="utf-8") as f:
        return json.load(f)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def match(kb, dtcs=(), symptom_text=""):
    """Rank KB issues against observed DTCs and free-text symptoms.

    Scoring: 3 points per DTC hit, 1 per symptom-keyword hit.
    Returns list of (score, issue) sorted best-first.
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
