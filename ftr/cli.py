"""Interactive CLI for ford-tdci-recovery."""

import json
import time
from datetime import datetime
from pathlib import Path

from . import obd
from .backup import take_snapshot

CHECKLIST_PATH = Path(__file__).resolve().parent.parent / "docs" / "POST_BATTERY_PROCEDURE.md"

MENU = """
ford-tdci-recovery
  1. FULL BACKUP snapshot (do this first!)
  2. Read fault codes
  3. Clear fault codes (backup enforced)
  4. Live DPF differential pressure
  5. Post-battery-replacement recovery checklist
  6. Raw OBD command
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
        return
    print(f"{len(codes)} stored fault code(s):")
    for c in codes:
        note = obd.KNOWN_DTC.get(c, "")
        print(f"  {c}  {('- ' + note) if note else ''}")


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
        with open(CHECKLIST_PATH, encoding="utf-8") as f:
            print(f.read())
    except FileNotFoundError:
        print(f"Checklist file not found at {CHECKLIST_PATH}")


def cmd_raw(ecu):
    cmd = input("Raw OBD command (e.g. '22 F4 2B' or '01 0C'): ").strip()
    print("\n".join(ecu.query(cmd)) or "NO DATA")


def run(ecu):
    backed_up = False
    while True:
        print(MENU)
        choice = input("Select: ").strip()
        if choice == "1":
            cmd_backup(ecu)
            backed_up = True
        elif choice == "2":
            cmd_read_dtcs(ecu)
        elif choice == "3":
            backed_up = cmd_clear_dtcs(ecu, backed_up)
        elif choice == "4":
            cmd_live_dpf(ecu)
        elif choice == "5":
            cmd_checklist()
        elif choice == "6":
            cmd_raw(ecu)
        elif choice == "0":
            break


def run_demo(ecu):
    print("=== DEMO MODE (simulated ECU) ===\n")
    cmd_backup(ecu)
    print()
    cmd_read_dtcs(ecu)
    print("\nDemo complete. Run without --demo against a real adapter.")
