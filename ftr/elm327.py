"""Cross-platform ELM327 transport (USB or Bluetooth serial) + simulated ECU."""

import time


class ELM327:
    """Minimal ELM327 serial driver.

    Works with any adapter that presents a serial port:
      - Windows USB cable          -> COMx
      - Windows paired Bluetooth   -> COMx (outgoing port)
      - Linux Bluetooth (rfcomm)   -> /dev/rfcomm0
    """

    def __init__(self, port=None, baud=38400, timeout=3):
        try:
            import serial
            from serial.tools import list_ports
        except ImportError:
            raise SystemExit(
                "pyserial is not installed. Run:  pip install -r requirements.txt\n"
                "(or test without hardware using:  python ford_recovery.py --demo)"
            )
        if port is None:
            ports = [p.device for p in list_ports.comports()]
            if not ports:
                raise SystemExit(
                    "No serial ports found.\n"
                    "  Windows: pair the adapter, then check Bluetooth 'More options' "
                    "for the outgoing COM port.\n"
                    "  Linux:   rfcomm bind 0 <adapter-MAC>  then use /dev/rfcomm0"
                )
            print("Available serial ports:")
            for i, p in enumerate(ports):
                print(f"  [{i}] {p}")
            choice = input("Select number, or type a port (COM5 / /dev/rfcomm0): ").strip()
            port = ports[int(choice)] if choice.isdigit() else choice
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        for init in ("ATZ", "ATE0", "ATL0", "ATS0", "ATH1", "ATSP0"):
            self.query(init)
            time.sleep(0.4 if init == "ATZ" else 0.05)

    def query(self, cmd):
        """Send one command, return cleaned response lines."""
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


class SimulatedECU:
    """Canned ELM327 responses so the whole tool can be tested without a car."""

    def query(self, cmd):
        cmd = cmd.replace(" ", "").upper()
        time.sleep(0.02)
        if cmd.startswith("AT"):
            if cmd == "ATZ":
                return ["ELM327 v1.5"]
            if cmd == "ATI":
                return ["ELM327 v1.5"]
            if cmd == "ATRV":
                return ["12.6V"]
            if cmd == "ATDP":
                return ["ISO 15765-4 (CAN 11/500)"]
            return ["OK"]
        if cmd == "0100":
            return ["41 00 BE 1F B8 13"]
        if cmd == "0101":
            return ["41 01 82 07 65 00"]  # MIL on, 2 DTCs
        if cmd == "010C":
            return ["41 0C 0D 48"]
        if cmd == "0105":
            return ["41 05 7A"]
        if cmd == "010B":
            return ["41 0B 63"]
        if cmd == "03":
            return ["43 24 53 24 63"]      # P2453 + P2463
        if cmd == "04":
            return ["44"]
        if cmd == "0902":                  # VIN (simplified single-frame form)
            return ["49 02 01 57 46 30 4D 58 58 4B 55 47 41 31 32 33 34 35 36 37"]
        if cmd == "0904":
            return ["49 04 01 41 42 31 32 2D 31 34 43 30 34 36 2D 41 41"]
        if cmd == "0906":
            return ["49 06 01 1A 2B 3C 4D"]
        if cmd == "090A":
            return ["49 0A 01 50 43 4D 5F 53 49 44 32 30 36"]
        if cmd.startswith("22"):
            return ["62 " + cmd[2:4] + " " + cmd[4:6] + " 01 2C"]
        return ["NO DATA"]

    def close(self):
        pass
