#!/usr/bin/env python3
"""
Ford 2.0 TDCi DPF Diagnostic Tool
=================================
Read-only / service diagnostics for ELM327 adapters (USB or Bluetooth).

What it does:
  - Connects to an ELM327 on a Windows COM port (USB cable or paired Bluetooth)
  - Reads and decodes fault codes (DTCs), with Ford DPF-specific descriptions
  - Clears fault codes (with confirmation)
  - Shows live engine data (RPM, speed, coolant temp, boost/intake pressure)
  - Queries custom Ford Mode-22 PIDs (e.g. DPF differential pressure) - the PID
    table is configurable; confirm exact PIDs/scaling against FORScan docs
  - Logs live sessions to CSV

What it deliberately does NOT do:
  - Emulate, spoof, or override the DPF pressure sensor signal. That is not
    possible through ELM327 (the sensor is a hardwired ECM input) and emissions
    defeat is illegal for road vehicles. Use this tool to find the real fault.

Usage:
  python dpf_tool.py              # interactive menu
  python dpf_tool.py --demo       # scripted run against a simulated ECU
  python dpf_tool.py --port COM5  # skip port auto-detection

Requires: pip install pyserial   (only for a real adapter; --demo needs nothing)
"""

import argparse
import csv
import sys
import time
from datetime import datetime

# --------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------

class SimulatedECU:
    """Canned ELM327 responses so the tool can be tested without a car."""

    def __init__(self):
        self.headers = False

    def query(self, cmd):
        cmd = cmd.replace(" ", "").upper()
        time.sleep(0.05)
        if cmd.startswith("AT"):
            if cmd == "ATZ":
                return ["ELM327 v1.5"]
            return ["OK"]
        if cmd == "0100":
            return ["41 00 BE 1F B8 13"]  # many PIDs supported
        if cmd == "010C":   # RPM: ((A*256)+B)/4
            return ["41 0C 0D 48"]       # ~850 rpm idle
        if cmd == "010D":
            return ["41 0D 00"]
        if cmd == "0105":
            return ["41 05 7A"]          # 82 C coolant
        if cmd == "010B":
            return ["41 0B 63"]          # 99 kPa intake manifold
        if cmd == "03":     # stored DTCs: P2453 and P2463 as an example
            return ["43 24 53 24 63"]
        if cmd == "04":
            return ["44"]
        if cmd.startswith("22"):
            # Simulated Mode-22 response: raw DPF pressure bytes
            return ["62 " + cmd[2:4] + " " + cmd[4:6] + " 01 2C"]
        return ["NO DATA"]

    def close(self):
        pass


class ELM327:
    """Minimal ELM327 serial driver (works over USB or Bluetooth COM ports)."""

    def __init__(self, port=None, baud=38400, timeout=2):
        try:
            import serial
            from serial.tools import list_ports
        except ImportError:
            raise SystemExit(
                "pyserial is not installed. Run:  pip install pyserial\n"
                "(or test without hardware using:  python dpf_tool.py --demo)"
            )
        if port is None:
            ports = [p.device for p in list_ports.comports()]
            if not ports:
                raise SystemExit("No COM ports found. Is the adapter plugged in / paired?")
            print("Available COM ports:")
            for i, p in enumerate(ports):
                print(f"  [{i}] {p}")
            choice = input("Select port number (or type e.g. COM5): ").strip()
            port = ports[int(choice)] if choice.isdigit() else choice.upper()
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        for init in ("ATZ", "ATE0", "ATL0", "ATS0", "ATH1", "ATSP0"):
            self.query(init)
            time.sleep(0.3 if init == "ATZ" else 0.05)

    def query(self, cmd):
        self.ser.reset_input_buffer()
        self.ser.write((cmd.strip() + "\r").encode())
        raw = self.ser.read_until(b">").decode(errors="replace")
        lines = []
        for line in raw.replace("\r", "\n").split("\n"):
            line = line.strip().strip(">")
            if line and line.upper() not in ("OK", "?", "SEARCHING...", cmd.upper()):
                lines.append(line)
        return lines

    def close(self):
        self.ser.close()


# --------------------------------------------------------------------------
# Decoding helpers
# --------------------------------------------------------------------------

KNOWN_DPCS = {
    "P2002": "DPF efficiency below threshold (Bank 1) - often hoses/sensor, sometimes a genuinely blocked DPF",
    "P242F": "DPF restriction - ash accumulation",
    "P2452": "DPF pressure sensor 'A' circuit - wiring/connector fault",
    "P2453": "DPF pressure sensor 'A' circuit range/performance - check hoses & sensor first",
    "P2454": "DPF pressure sensor 'A' circuit low",
    "P2455": "DPF pressure sensor 'A' circuit high",
    "P2463": "DPF restriction - soot accumulation (forced regen or cleaning needed)",
    "P246C": "DPF restriction - power forced limited (limp mode active)",
    "P244A": "DPF differential pressure too low during regeneration",
}

LETTERS = "PCBU"

def decode_dtcs(lines):
    data = []
    for line in lines:
        parts = line.split()
        if parts and parts[0] == "43":
            data.extend(parts[1:])
    codes = []
    for i in range(0, len(data) - 1, 2):
        b1, b2 = int(data[i], 16), int(data[i + 1], 16)
        if b1 == 0 and b2 == 0:
            continue
        codes.append(f"{LETTERS[(b1 >> 6) & 3]}{(b1 >> 4) & 3}{b1 & 0xF:X}{b2:02X}")
    return codes


def data_bytes(lines, positive_id):
    for line in lines:
        parts = line.split()
        if parts and parts[0] == positive_id:
            return [int(p, 16) for p in parts[1:]]
        # Mode-22 positive response: 62 <pid_hi> <pid_lo> <data...>
        if len(parts) > 3 and parts[0] == "62" and "".join(parts[1:3]) == positive_id:
            return [int(p, 16) for p in parts[3:]]
    return None


# --------------------------------------------------------------------------
# Custom (Ford Mode-22) PID table
# --------------------------------------------------------------------------
# Exact DPF pressure PID addresses and scaling vary by ECU (SID206/SID208 etc).
# Confirm against FORScan's PID list for your PCM before trusting values.
# Bytes are always shown raw so you can sanity-check any scaling yourself.

CUSTOM_PIDS = {
    "DPF differential pressure (example PID - verify!)": {
        "request": "22 F4 2B",
        "scale": lambda b: (b[0] * 256 + b[1]) / 100.0 if b and len(b) >= 2 else None,
        "unit": "kPa (?)",
    },
}


# --------------------------------------------------------------------------
# Tool actions
# --------------------------------------------------------------------------

def action_read_dtcs(ecu):
    codes = decode_dtcs(ecu.query("03"))
    if not codes:
        print("No stored fault codes.")
        return
    print(f"{len(codes)} stored fault code(s):")
    for c in codes:
        note = KNOWN_DPCS.get(c, "")
        print(f"  {c}  {('- ' + note) if note else ''}")
    dpf = [c for c in codes if c in KNOWN_DPCS]
    if dpf:
        print("\nDPF-related codes present. Before replacing anything:")
        print("  1. Inspect the two sensor hoses for splits/soot blockage")
        print("  2. Check the loom near the sensor plug for a broken wire")
        print("  3. Read live DPF pressure (menu option 4): ~0-3 kPa at idle is healthy;")


def action_clear_dtcs(ecu):
    confirm = input("Really clear all fault codes? This also resets readiness "
                    "monitors (type YES): ").strip()
    if confirm != "YES":
        print("Cancelled.")
        return
    resp = ecu.query("04")
    print("Codes cleared." if any("44" in r for r in resp) else f"Unexpected response: {resp}")
    print("Note: after replacing the sensor, Ford learned-value resets need FORScan.")


def action_live_standard(ecu):
    print("Live data (Ctrl+C to stop)\n")
    try:
        while True:
            row = {"time": datetime.now().strftime("%H:%M:%S")}
            b = data_bytes(ecu.query("010C"), "41")
            row["RPM"] = ((b[1] * 256 + b[2]) // 4) if b else "?"
            b = data_bytes(ecu.query("010D"), "41")
            row["Speed_kmh"] = b[1] if b else "?"
            b = data_bytes(ecu.query("0105"), "41")
            row["Coolant_C"] = (b[1] - 40) if b else "?"
            b = data_bytes(ecu.query("010B"), "41")
            row["Intake_kPa"] = b[1] if b else "?"
            print("  ".join(f"{k}={v}" for k, v in row.items()))
            time.sleep(1.0)
    except KeyboardInterrupt:
        print()


def action_dpf_pressure(ecu, log_to_csv=False):
    writer = None
    f = None
    if log_to_csv:
        fname = f"dpf_log_{datetime.now():%Y%m%d_%H%M%S}.csv"
        f = open(fname, "w", newline="")
        writer = csv.writer(f)
        writer.writerow(["time", "pid", "raw_hex", "scaled", "unit"])
        print(f"Logging to {fname}")
    print("DPF pressure readout (Ctrl+C to stop). Healthy idle: roughly 0-3 kPa.\n")
    try:
        while True:
            for name, spec in CUSTOM_PIDS.items():
                lines = ecu.query(spec["request"])
                pos = "".join(spec["request"].split()[1:3])
                b = data_bytes(lines, pos)
                scaled = spec["scale"](b) if b else None
                raw = " ".join(f"{x:02X}" for x in b) if b else "NO DATA"
                print(f"{datetime.now():%H:%M:%S}  {name}: raw=[{raw}] "
                      f"scaled={scaled if scaled is not None else '?'} {spec['unit']}")
                if writer:
                    writer.writerow([datetime.now().isoformat(), spec["request"],
                                     raw, scaled, spec["unit"]])
            time.sleep(1.0)
    except KeyboardInterrupt:
        print()
    finally:
        if f:
            f.close()


def action_custom_query(ecu):
    cmd = input("Enter raw OBD command (e.g. '22 F4 2B' or '01 0C'): ").strip()
    print("\n".join(ecu.query(cmd)) or "NO DATA")


MENU = """
Ford 2.0 TDCi DPF Diagnostic Tool
  1. Read fault codes
  2. Clear fault codes
  3. Live standard data (RPM/speed/coolant/intake)
  4. DPF differential pressure (live, optional CSV log)
  5. Raw OBD command
  0. Exit
"""


def run_interactive(ecu):
    while True:
        print(MENU)
        choice = input("Select: ").strip()
        if choice == "1":
            action_read_dtcs(ecu)
        elif choice == "2":
            action_clear_dtcs(ecu)
        elif choice == "3":
            action_live_standard(ecu)
        elif choice == "4":
            action_dpf_pressure(ecu, log_to_csv=input("Log to CSV? [y/N]: ").lower() == "y")
        elif choice == "5":
            action_custom_query(ecu)
        elif choice == "0":
            break


def run_demo(ecu):
    print("=== DEMO MODE (simulated ECU) ===")
    action_read_dtcs(ecu)
    print("\n--- Single DPF pressure sample ---")
    for name, spec in CUSTOM_PIDS.items():
        lines = ecu.query(spec["request"])
        b = data_bytes(lines, "".join(spec["request"].split()[1:3]))
        print(f"{name}: raw=[{' '.join(f'{x:02X}' for x in b)}] "
              f"scaled={spec['scale'](b)} {spec['unit']}")
    print("\nDemo complete. Connect a real adapter and run without --demo.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true", help="run scripted demo on a simulated ECU")
    ap.add_argument("--port", help="COM port, e.g. COM5")
    args = ap.parse_args()

    if args.demo:
        ecu = SimulatedECU()
        run_demo(ecu)
        return

    print("Ignition ON (engine off is fine for code reading).")
    ecu = ELM327(port=args.port)
    try:
        run_interactive(ecu)
    finally:
        ecu.close()


if __name__ == "__main__":
    main()
