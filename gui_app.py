#!/usr/bin/env python3
"""
gui_app.py — desktop GUI for ford-tdci-recovery (Linux Mint / Windows).

  python gui_app.py          # opens in SIMULATION mode (fake car, no hardware)
  python gui_app.py --real   # real ELM327 adapter (enter port, untick Simulation)

Linux Mint: if tkinter is missing ->  sudo apt install python3-tk
"""

import argparse

from ftr.gui import DiagApp


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--real", action="store_true",
                    help="start in real-adapter mode instead of simulation")
    args = ap.parse_args()
    DiagApp(simulate=not args.real).mainloop()


if __name__ == "__main__":
    main()
