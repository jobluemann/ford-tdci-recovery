#!/usr/bin/env python3
"""
ford-tdci-recovery
==================
Backup-first open-source diagnostic suite for Ford 2.0 TDCi (Kuga Mk2 /
Focus Mk3 platform). Cross-platform (Windows portable, Linux Mint) over
ELM327 USB or Bluetooth. See README.md and docs/ARCHITECTURE.md.

  python ford_recovery.py                 interactive menu
  python ford_recovery.py --demo          simulated vehicle
  python ford_recovery.py --serve 8765    HTTP bridge for the PWA (phone UI)
"""

import argparse

from ftr.cli import run, run_demo
from ftr.elm327 import ELM327, SimulatedECU
from ftr.modules import SimulatedVehicle


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true",
                    help="run against a simulated vehicle (no hardware needed)")
    ap.add_argument("--port", help="serial port, e.g. COM5 or /dev/rfcomm0")
    ap.add_argument("--serve", type=int, metavar="PORT",
                    help="run the HTTP bridge for the PWA instead of the menu")
    args = ap.parse_args()

    if args.demo and not args.serve:
        run_demo(SimulatedECU())
        return

    if args.serve:
        from ftr.server import serve
        if args.demo:
            serve(SimulatedECU(), SimulatedVehicle(), args.serve)
            return
        print("Ignition ON (engine off is fine).")
        ecu = ELM327(port=args.port)
        try:
            serve(ecu, ecu, args.serve)
        finally:
            ecu.close()
        return

    print("Ignition ON (engine off is fine).")
    ecu = ELM327(port=args.port)
    try:
        run(ecu)
    finally:
        ecu.close()


if __name__ == "__main__":
    main()
