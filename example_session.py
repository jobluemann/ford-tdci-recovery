#!/usr/bin/env python3
"""End-to-end example session against the SIMULATED car, rendered as a report.

Runs the exact flow a mechanic would: backup -> fault codes -> module scan ->
symptom lookup -> AI diagnosis (live, if a key is configured). Output is a
Markdown report at docs/EXAMPLE_SESSION.md. Safe to run any time: the "car"
is simulated (demo_fake_car.py) and the VIN is fake.

    python example_session.py
"""

import datetime
import time
from pathlib import Path

from demo_fake_car import FakeKuga
from ftr import aichat, aiconfig, known_issues, modules
from ftr.backup import take_snapshot

REPORT = Path(__file__).resolve().parent / "docs" / "EXAMPLE_SESSION.md"

# The owner's real symptom list (from the actual Kuga this tool was built for)
SESSIONS = [
    ("Post-battery lag",
     "Vehicle is laggy after a battery replacement. Manual BMS reset and "
     "brake-pedal reset already done by a professional. Code P062F present. "
     "What is happening and what is the honest fix path?"),
    ("DPF pressure codes / limp mode",
     "DPF fault codes P2453 and P2463, car in limp mode. Is the DPF itself "
     "dead, or is something cheaper usually the cause on this engine?"),
    ("Gear scratch 1-2-3",
     "Automatic gearbox scratches between gears 1, 2 and 3 when shifting. "
     "Known issue on this model? Most likely cause and first checks?"),
    ("AWD dead, no dash warning",
     "All-wheel drive is not engaging but the dashboard shows no fault at "
     "all. How can that be, and where do I look first?"),
    ("Coolant in the oil",
     "There are signs of coolant mixing into the engine oil. What are the "
     "possible causes on the 2.0 TDCi, in order of likelihood?"),
]


def main():
    aiconfig.apply()
    lines = []
    w = lines.append
    w("# Example Diagnostic Session — Ford Kuga Mk2 2.0 TDCi (simulated)")
    w("")
    w(f"*Generated {datetime.date.today()} by `example_session.py` against the "
      "scripted fake car. VIN and codes are simulated but match the real "
      "vehicle's actual fault set.*")
    w("")

    # ---- 1. backup ----
    car = FakeKuga()
    fname, snap = take_snapshot(car)
    w("## 1. Backup snapshot (always first)")
    w("")
    w(f"- saved: `{fname}`")
    w(f"- VIN (fake): `{snap['vehicle'].get('vin')}`")
    w(f"- ECU: `{snap['vehicle'].get('ecu_name')}`  "
      f"calibration `{snap['vehicle'].get('calibration_id')}`")
    mil = snap["status"].get("mil", {})
    w(f"- MIL on: {mil.get('mil_on')}, {mil.get('dtc_count')} stored codes")
    w("")

    # ---- 2. module scan ----
    w("## 2. Full module scan (what the dashboard hides)")
    w("")
    w("```")
    scan_log = []
    modules.scan_modules(car, log=scan_log.append)
    lines.extend(scan_log)
    w("```")
    w("")

    # ---- 3+4. per-issue: KB verdict + AI diagnosis ----
    kb = known_issues.load_kb()
    ai_on = aiconfig.configured()
    w(f"## 3. Symptom-by-symptom: known-issue verdict + AI diagnosis")
    w("")
    if not ai_on:
        w("*(AI key not configured — KB verdicts only)*")
        w("")
    for i, (title, question) in enumerate(SESSIONS, 1):
        w(f"### 3.{i} {title}")
        w("")
        w(f"> Owner says: \"{question}\"")
        w("")
        hits = known_issues.match(kb, symptom_text=question,
                                  dtcs=[w2 for w2 in question.split()
                                        if w2.startswith(("P0", "P2", "U0", "C1"))])
        if hits:
            score, issue, dh, sh = hits[0]
            w(f"**KB verdict: {issue['known_issue'].upper()} known issue "
              f"(confidence: {issue['confidence']})** — {issue['title']}")
            if dh:
                w(f"- matching codes: {', '.join(dh)}")
            w(f"- most likely cause: {issue['likely_causes'][0]}")
            srcs = issue.get("sources", [])
            if srcs:
                w(f"- sources: {'; '.join(srcs[:2])}")
        else:
            w("**KB verdict: no match**")
        w("")
        if ai_on:
            try:
                reply, _ = aichat.chat_grounded(question)
                w("**AI diagnosis (two-model pipeline: gpt-oss-20b research → "
                  "qwen3.6-27b diagnostics, grounded in the KB):**")
                w("")
                w(reply.strip())
            except Exception as e:
                w(f"*(AI request failed: {e})*")
            w("")
            time.sleep(10)  # stay well inside Groq free-tier rate limits

    w("---")
    w("*Every issue above is a documented, sourced known fault for this "
      "vehicle — the dealer-money-trap scenario this project exists to "
      "prevent.*")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"report written: {REPORT}")


if __name__ == "__main__":
    main()
