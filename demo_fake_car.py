#!/usr/bin/env python3
"""
demo_fake_car.py — full-suite demo against a scripted 'owner's car'.

Simulates the exact symptom profile described by the owner:
  - laggy throttle after a battery replacement (P062F in PCM)
  - DPF pressure faults (P2453, P2463)
  - Powershift scratching/harsh shifts 1-2-3 (P0776 in TCM)
  - AWD not engaging with NO dashboard warning (P1889 hidden in DEM)

Runs: backup snapshot -> full module scan -> known-issue matching against
the owner's own words. No hardware needed.
"""

from ftr import known_issues, modules, obd
from ftr.backup import take_snapshot

OWNER_SYMPTOMS = (
    "laggy throttle after battery swap, scratch between gears 1 2 3, "
    "AWD not engaging, no warning light on dashboard"
)


class FakeKuga:
    """The owner's car, scripted: per-module answers + Mode 01/03/09."""

    UDS_DTCS = {
        "7E0": ["59 02 FF 24 53 2F 09 24 63 2F 09 06 2F 00 09"],
        #        PCM: P2453-2F, P2463-2F, P062F-00  (all active+confirmed)
        "7E1": ["59 02 FF 07 76 00 09"],            # TCM: P0776-00
        "760": ["59 02 FF"],                        # ABS: clean
        "720": ["59 02 FF"],                        # cluster: clean (dash shows nothing!)
        "726": ["59 02 FF"],                        # BCM: clean
        "737": ["59 02 FF"],                        # airbag: clean
        "761": ["59 02 FF 18 89 00 09"],            # DEM: P1889-00 — the silent AWD fault
    }

    def __init__(self):
        self.header = "7E0"

    def query(self, cmd):
        c = cmd.strip().upper()
        if c.startswith("AT"):
            if c.startswith("AT SH"):
                self.header = c.split()[-1]
            if c == "ATI":
                return ["ELM327 v1.5"]
            if c == "ATRV":
                return ["12.4V"]
            if c == "ATDP":
                return ["ISO 15765-4 (CAN 11/500)"]
            return ["OK"]
        if c == "3E 00":
            return ["7E 00"] if self.header in self.UDS_DTCS else []
        if c == "19 02 AF":
            return self.UDS_DTCS.get(self.header, ["NO DATA"])
        # OBD-side answers (PCM)
        c2 = c.replace(" ", "")
        if c2 == "0100":
            return ["41 00 BE 1F B8 13"]
        if c2 == "0101":
            return ["41 01 83 07 65 00"]     # MIL on, 3 DTCs
        if c2 == "03":
            return ["43 24 53 24 63 60 2F"]  # P2453, P2463, P062F
        if c2 == "0902":
            return ["49 02 01 57 46 30 4D 58 58 4B 55 47 41 39 38 37 36 35 34 33"]
        if c2 == "0904":
            return ["49 04 01 41 42 31 32 2D 31 34 43 30 34 36 2D 41 41"]
        if c2 == "0906":
            return ["49 06 01 1A 2B 3C 4D"]
        if c2 == "090A":
            return ["49 0A 01 50 43 4D 5F 53 49 44 32 30 38"]
        if c2 == "22F42B":
            return ["62 F4 2B 01 2C"]        # DPF pressure raw
        return ["NO DATA"]

    def close(self):
        pass


def main():
    car = FakeKuga()
    print("=" * 64)
    print("DEMO: the owner's Kuga, scripted — full suite run")
    print("=" * 64)

    print("\n### 1. BACKUP SNAPSHOT (before anything)\n")
    fname, snap = take_snapshot(car)
    print(f"saved: {fname}")
    print(f"VIN: {snap['vehicle']['vin']}  ECU: {snap['vehicle']['ecu_name']}  "
          f"cal: {snap['vehicle']['calibration_id']}")
    print(f"MIL: {snap['status']['mil']}")

    print("\n### 2. FULL MODULE SCAN (what the dashboard hides)\n")
    modules.scan_modules(car)

    pcm_codes = obd.decode_dtcs(car.query("03"))
    print("\n### 3. KNOWN-ISSUE MATCHING against the owner's own words")
    print(f"    \"{OWNER_SYMPTOMS}\"\n")
    kb = known_issues.load_kb()
    hits = known_issues.match(kb, dtcs=pcm_codes, symptom_text=OWNER_SYMPTOMS)
    # fold in the hidden module codes too
    hidden = ["P0776", "P1889"]
    hits = known_issues.match(kb, dtcs=pcm_codes + hidden, symptom_text=OWNER_SYMPTOMS)
    for score, issue, dh, sh in hits:
        print(known_issues.render(score, issue, dh, sh))
        print()

    print("### VERDICT (simulated) ###")
    print("Four separate known issues, one car — exactly the dealer-money-trap")
    print("scenario this project exists to prevent.")


if __name__ == "__main__":
    main()
