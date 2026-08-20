"""Interactive CLI for ford-tdci-recovery."""

import json
import time
from datetime import datetime
from pathlib import Path

from . import obd, known_issues, modules, feeds, aichat, share
from .backup import take_snapshot

ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_PATH = ROOT / "docs" / "POST_BATTERY_PROCEDURE.md"

MENU = """
ford-tdci-recovery
  1. FULL BACKUP snapshot (do this first!)
  2. Read fault codes (PCM)
  3. Clear fault codes (backup enforced)
  4. Live DPF differential pressure
  5. Post-battery-replacement recovery checklist
  6. Raw OBD command
 --- full-vehicle suite ---
  7. Module scan (PCM/TCM/ABS/IPC/BCM/RCM/DEM)
  8. Symptom & known-issue lookup
  9. Forum/RSS symptom search
 10. AI assistant (optional, env-configured)
 11. Share anonymized report with community platform
  0. Exit
"""


def cmd_backup(ecu):
    print("Taking full readable-state snapshot...")
    fname, snap = take_snapshot(ecu)
    print(f"Backup saved: {fname}")
    print(json.dumps(snap["vehicle"], indent=2))
    print(json.dumps(snap["status"].get("mil"), indent=2))
    return fname


def cmd_read_dtcs(ecu):
    codes = obd.decode_dtcs(ecu.query("03"))
    if not codes:
        print("No stored fault codes.")
        return []
    print(f"{len(codes)} stored fault code(s):")
    for c in codes:
        note = obd.KNOWN_DTC.get(c, "")
        print(f"  {c}  {('- ' + note) if note else ''}")
    return codes


def cmd_clear_dtcs(ecu, backed_up):
    if not backed_up:
        print("Refusing to clear before a backup. Run option 1 first.")
        return False
    confirm = input("Clear all fault codes? This resets readiness monitors "
                    "(type YES): ").strip()
    if confirm != "YES":
        print("Cancelled.")
        return backed_up
    resp = ecu.query("04")
    ok = any("44" in r for r in resp)
    print("Codes cleared." if ok else f"Unexpected response: {resp}")
    return backed_up


def cmd_live_dpf(ecu, dpf_pid="22 F4 2B"):
    print("DPF pressure (Ctrl+C to stop). Healthy idle: roughly 0-3 kPa.")
    pid_key = "".join(dpf_pid.split()[1:3])
    try:
        while True:
            b = obd.data_bytes(ecu.query(dpf_pid), pid_key)
            if b and len(b) >= 2:
                raw = (b[0] << 8) | b[1]
                print(f"{datetime.now():%H:%M:%S}  raw={raw} "
                      f"(~{raw / 100.0:.2f} kPa if scaling is /100 - verify!)")
            else:
                print(f"{datetime.now():%H:%M:%S}  NO DATA")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print()


def cmd_checklist():
    try:
        print(CHECKLIST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Checklist file not found at {CHECKLIST_PATH}")


def cmd_raw(ecu):
    cmd = input("Raw OBD command (e.g. '22 F4 2B' or '01 0C'): ").strip()
    print("\n".join(ecu.query(cmd)) or "NO DATA")


def cmd_module_scan(vehicle):
    print("Scanning all known Ford modules (needs HS/MS-CAN switch for full coverage)...\n")
    results = modules.scan_modules(vehicle)
    n_faults = sum(len(d) for _, d in results.values())
    print(f"\nScan complete: {sum(1 for p, _ in results.values() if p)} module(s) "
          f"answered, {n_faults} fault entrie(s).")
    return results


def cmd_symptom_lookup(last_dtcs):
    kb = known_issues.load_kb()
    text = input("Describe symptoms (e.g. 'scratch between gears 1 2 3'):\n> ")
    hits = known_issues.match(kb, dtcs=last_dtcs, symptom_text=text)
    if not hits:
        print("No KB match. Try different wording, the forum search (menu 9), "
              "or contribute this issue via pull request once diagnosed.")
        return []
    print()
    for score, issue, dtc_hits, sym_hits in hits:
        print(known_issues.render(score, issue, dtc_hits, sym_hits))
        print()
    print(kb["disclaimer"])
    return [i["id"] for _, i, _, _ in hits]


def cmd_forum_search():
    cfg = ROOT / "data" / "feeds.json"
    feed_list = feeds.DEFAULT_FEEDS
    if cfg.exists():
        feed_list = json.loads(cfg.read_text(encoding="utf-8"))["feeds"]
    if not feed_list:
        print("No feeds configured. Add forum RSS URLs to data/feeds.json "
              "as {\"feeds\": [\"https://...\"]}")
        return
    kw = input("Keywords (space separated, all must match): ").split()
    if not kw:
        return
    results, errors = feeds.search(feed_list, kw)
    for e in errors:
        print(f"(feed unavailable, using cache: {e})")
    print(f"\n{len(results)} result(s):")
    for it in results[:15]:
        print(f"  - {it['title']}\n    {it['link']}")


def cmd_ai_chat(snapshot_path):
    kb = known_issues.load_kb()
    kb_text = json.dumps(kb["issues"])[:8000]
    history = []
    print("AI assistant ('quit' to exit). VIN is stripped from context.\n")
    while True:
        q = input("you> ").strip()
        if q.lower() in ("quit", "exit", ""):
            break
        history.append({"role": "user", "content": q})
        try:
            reply = aichat.chat(history, kb_text=kb_text, snapshot_path=snapshot_path)
        except Exception as e:
            reply = f"(request failed: {e})"
        history.append({"role": "assistant", "content": reply})
        print(f"\nai> {reply}\n")


def cmd_share(snapshot_path, matched_ids):
    if not snapshot_path:
        print("Run a backup snapshot first (menu 1).")
        return
    report = share.build_report(snapshot_path, matched_ids)
    print(json.dumps(report, indent=2))
    endpoint = share.default_endpoint() or input(
        "Share endpoint URL (blank to only save locally): ").strip()
    out = ROOT / "backups" / f"shared_report_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Local copy: {out}")
    if endpoint and input("POST this report? (type SHARE): ").strip() == "SHARE":
        try:
            print(f"Server responded: HTTP {share.post_report(endpoint, report)}")
        except Exception as e:
            print(f"Upload failed: {e}. Local copy kept.")


def run(ecu, vehicle=None):
    """ecu: OBD interface; vehicle: module-scan interface (defaults to ecu)."""
    vehicle = vehicle or ecu
    backed_up, snapshot_path, last_dtcs, matched = False, None, [], []
    while True:
        print(MENU)
        choice = input("Select: ").strip()
        if choice == "1":
            snapshot_path = cmd_backup(ecu)
            backed_up = True
        elif choice == "2":
            last_dtcs = cmd_read_dtcs(ecu)
        elif choice == "3":
            backed_up = cmd_clear_dtcs(ecu, backed_up)
        elif choice == "4":
            cmd_live_dpf(ecu)
        elif choice == "5":
            cmd_checklist()
        elif choice == "6":
            cmd_raw(ecu)
        elif choice == "7":
            cmd_module_scan(vehicle)
        elif choice == "8":
            matched = cmd_symptom_lookup(last_dtcs)
        elif choice == "9":
            cmd_forum_search()
        elif choice == "10":
            cmd_ai_chat(snapshot_path)
        elif choice == "11":
            cmd_share(snapshot_path, matched)
        elif choice == "0":
            break


def run_demo(ecu):
    print("=== DEMO MODE (simulated vehicle) ===\n")
    cmd_backup(ecu)
    print()
    dtcs = cmd_read_dtcs(ecu)
    print("\n--- Module scan (simulated whole vehicle) ---\n")
    cmd_module_scan(modules.SimulatedVehicle())
    print("\n--- Symptom lookup demo: 'banging into gear and jerky shifts' ---\n")
    kb = known_issues.load_kb()
    for score, issue, dh, sh in known_issues.match(kb, dtcs=dtcs, symptom_text="banging into gear and jerky shifts"):
        print(known_issues.render(score, issue, dh, sh))
        print()
    print("Demo complete. Run without --demo against a real adapter.")
