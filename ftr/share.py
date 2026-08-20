"""Share an anonymized diagnostic report with the community data platform.

The VIN is stripped and replaced by a one-way hash prefix so repeat reports
from the same vehicle can be correlated without exposing identity. Nothing
is sent unless the user confirms in the CLI.
"""

import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone


def build_report(snapshot_path, matched_issue_ids=()):
    with open(snapshot_path, encoding="utf-8") as f:
        snap = json.load(f)
    vin = snap.get("vehicle", {}).get("vin") or ""
    report = {
        "schema": "ftr-report/1",
        "submitted_utc": datetime.now(timezone.utc).isoformat(),
        "vehicle_ref": hashlib.sha256(vin.encode()).hexdigest()[:12] if vin else None,
        "ecu_name": snap.get("vehicle", {}).get("ecu_name"),
        "calibration_id": snap.get("vehicle", {}).get("calibration_id"),
        "fault_codes": [c["code"] for c in snap.get("fault_codes", [])],
        "matched_known_issues": list(matched_issue_ids),
    }
    return report


def post_report(endpoint, report, timeout=20):
    body = json.dumps(report).encode()
    req = urllib.request.Request(
        endpoint, data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "ford-tdci-recovery/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def default_endpoint():
    return os.environ.get("FTR_SHARE_ENDPOINT", "")
