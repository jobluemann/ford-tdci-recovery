#!/usr/bin/env python3
"""
pcm_flasher.py — in-vehicle UDS flash tool (expert mode).

YOU MUST SUPPLY:
  --config    JSON flash plan with your ECU's session/security/routine IDs
  --file      firmware container (.vbf) or raw .bin with --load-address
  --seedkey   path to YOUR python module exposing:
                  def compute_key(level: int, seed: bytes) -> bytes
              (your own seed/key implementation — none is shipped here)

Safety: wired adapters only for real flashes (ELM327 over USB is the minimum;
a STN-based or J-2534 adapter is strongly preferred). A battery maintainer
holding >= 12.4 V is mandatory. Flashing over Bluetooth is refused unless
you pass --allow-bluetooth.

Test the entire flow offline first:
  python pcm_flasher.py --demo
"""

import argparse
import importlib.util
import sys

from ftr.flasher import (FlashAbort, SimulatedUDSECU, demo_key_fn, flash,
                         load_plan)
from ftr.vbf import blocks_from_raw, parse_vbf, summarize


def load_seedkey(path):
    spec = importlib.util.spec_from_file_location("user_seedkey", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "compute_key"):
        raise SystemExit(f"{path} must define compute_key(level, seed) -> bytes")
    return mod.compute_key


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true",
                    help="flash a synthetic firmware image into the simulator")
    ap.add_argument("--config", help="flash plan JSON (see config/ example)")
    ap.add_argument("--file", help="firmware: .vbf container or raw .bin")
    ap.add_argument("--load-address", help="hex load address for raw .bin, e.g. 0x80020000")
    ap.add_argument("--seedkey", help="path to your compute_key python module")
    ap.add_argument("--port", help="serial port, e.g. COM5")
    ap.add_argument("--allow-bluetooth", action="store_true",
                    help="override the Bluetooth flash refusal (not recommended)")
    args = ap.parse_args()

    if args.demo:
        # build a synthetic 3 KB 'firmware' and run the full flow
        blocks = blocks_from_raw_bytes(0x80020000, bytes(range(256)) * 12)
        plan = {
            "session": {"extended": "03", "programming": "02"},
            "security": [{"seed_sub": "01", "key_sub": "02"}],
            "erase_routine": "FF00", "verify_routine": "FF01",
            "block_size": 128, "min_voltage": 12.2,
        }
        sim = SimulatedUDSECU()
        print(f"Demo firmware: {summarize(blocks)}")
        flash(sim, plan, blocks, demo_key_fn)
        assert len(sim.written) == 3072, "simulator did not receive all bytes"
        print(f"Simulator received {len(sim.written)} bytes — demo flash OK.")
        return

    for req in ("config", "file", "seedkey"):
        if not getattr(args, req):
            ap.error(f"--{req} is required for a real flash (or use --demo)")

    if not args.allow_bluetooth:
        warn = input(
            "Confirm you are on a WIRED adapter with a battery maintainer "
            "connected (type WIRED): ").strip()
        if warn != "WIRED":
            raise SystemExit("Aborted. Bluetooth flashing is unsafe; use a cable.")

    from ftr.elm327 import ELM327
    plan = load_plan(args.config)
    key_fn = load_seedkey(args.seedkey)

    if args.file.lower().endswith(".vbf"):
        header, blocks = parse_vbf(args.file)
        print("VBF header:", header)
    else:
        if not args.load_address:
            ap.error("--load-address is required for raw .bin files")
        header, blocks = blocks_from_raw(args.file, int(args.load_address, 16))

    print(f"Loaded firmware: {summarize(blocks)}")
    if input("Proceed with flash? (type FLASH): ").strip() != "FLASH":
        raise SystemExit("Aborted by user.")

    elm = ELM327(port=args.port)
    try:
        flash(elm, plan, blocks, key_fn)
    except FlashAbort as e:
        raise SystemExit(f"FLASH ABORTED: {e}")
    finally:
        elm.close()


def blocks_from_raw_bytes(address, data):
    from ftr.vbf import Block
    return [Block(address, data)]


if __name__ == "__main__":
    main()
