"""Full readable-state snapshot: capture everything before anything changes.

This is the 'backup first' core of the tool. It saves a timestamped JSON file
with adapter identity, vehicle identity (VIN, calibration, CVN), MIL/readiness
status, supported PID map, stored fault codes and a raw DPF-pressure sample.
"""

import json
import os
from datetime import datetime, timezone

from . import obd

TOOL_NAME = "ford-tdci-recovery"
TOOL_VERSION = "0.1.0"


def take_snapshot(ecu, out_dir="backups", dpf_pid="22 F4 2B"):
    snap = {
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "adapter": {},
        "vehicle": {},
        "status": {},
        "fault_codes": [],
        "notes": (
            "Snapshot of all state readable through a generic ELM327 interface. "
            "PATS immobilizer keys and module As-Built blocks are NOT readable "
            "via generic OBD; use FORScan (extended license for PATS) to export "
            "those before key or module work."
        ),
    }

    snap["adapter"]["id"] = (ecu.query("ATI") or ["?"])[0]
    snap["adapter"]["voltage"] = (ecu.query("ATRV") or ["?"])[0]
    snap["adapter"]["protocol"] = (ecu.query("ATDP") or ["?"])[0]

    snap["vehicle"]["vin"] = obd.get_vin(ecu)
    snap["vehicle"]["calibration_id"] = obd.get_calibration_id(ecu)
    snap["vehicle"]["cvn"] = obd.get_cvn(ecu)
    snap["vehicle"]["ecu_name"] = obd.get_ecu_name(ecu)

    snap["status"]["mil"] = obd.get_mil_status(ecu)
    snap["status"]["supported_pids"] = obd.supported_pids(ecu)

    codes = obd.decode_dtcs(ecu.query("03"))
    snap["fault_codes"] = [
        {"code": c, "description": obd.KNOWN_DTC.get(c, "")} for c in codes
    ]

    raw = ecu.query(dpf_pid)
    snap["dpf_pressure_sample"] = {"request": dpf_pid, "raw_response": raw}

    os.makedirs(out_dir, exist_ok=True)
    fname = os.path.join(
        out_dir, f"backup_{datetime.now():%Y%m%d_%H%M%S}.json"
    )
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2, ensure_ascii=False)
    return fname, snap
