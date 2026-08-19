#!/usr/bin/env python3
"""
ford-tdci-recovery
==================
Backup-first recovery diagnostics for Ford 2.0 TDCi (Kuga / Focus) after a
battery replacement or module power loss. Cross-platform (Windows portable,
Linux Mint) over ELM327 USB or Bluetooth. See README.md.

This tool never emulates, spoofs, or overrides sensor signals. It snapshots
all readable state before any change, decodes DPF-related faults, and guides
the legitimate re-learn / reset procedures.
"""

import argparse

from ftr.cli import run, run_demo
from ftr.elm327 import ELM327, SimulatedECU


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true",
                    help="run against a simulated ECU (no hardware needed)")
    ap.add_argument("--port", help="serial port, e.g. COM5 or /dev/rfcomm0")
    args = ap.parse_args()

    if args.demo:
        run_demo(SimulatedECU())
        return

    print("Ignition ON (engine off is fine).")
    ecu = ELM327(port=args.port)
    try:
        run(ecu)
    finally:
        ecu.close()


if __name__ == "__main__":
    main()
