"""OBD-II decoding helpers (DTCs, Mode-09 vehicle info, PID parsing)."""

import string

KNOWN_DTC = {
    "P2002": "DPF efficiency below threshold (Bank 1)",
    "P242F": "DPF restriction - ash accumulation",
    "P244A": "DPF differential pressure too low during regeneration",
    "P2452": "DPF pressure sensor 'A' circuit - wiring/connector fault",
    "P2453": "DPF pressure sensor 'A' circuit range/performance - check hoses & sensor first",
    "P2454": "DPF pressure sensor 'A' circuit low",
    "P2455": "DPF pressure sensor 'A' circuit high",
    "P2463": "DPF restriction - soot accumulation",
    "P246C": "DPF restriction - power forced limited (limp mode)",
    "P0562": "System voltage low - common after battery/charging issues",
    "P062F": "EEPROM error - module memory/settings fault",
    "U0100": "Lost communication with ECM/PCM",
    "U0300": "Control module software incompatibility",
}

_LETTERS = "PCBU"


def decode_dtcs(lines):
    """Decode Mode-03 response lines into a list of DTC strings."""
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
        codes.append(f"{_LETTERS[(b1 >> 6) & 3]}{(b1 >> 4) & 3}{b1 & 0xF:X}{b2:02X}")
    return codes


def data_bytes(lines, positive_id):
    """Extract data bytes from a positive response.

    positive_id: '41' for Mode 01, or 'F42B'-style PID for Mode 22.
    """
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == positive_id:
            return [int(p, 16) for p in parts[1:]]
        if len(parts) > 3 and parts[0] == "62" and "".join(parts[1:3]) == positive_id:
            return [int(p, 16) for p in parts[3:]]
    return None


def _ascii_from_mode09(lines, service):
    """Tolerant parser for Mode 09 vehicle-info responses.

    Handles both simple single-frame dumps and ISO-TP multiline output by
    collecting every hex byte from lines mentioning the positive response
    (0x49), then extracting printable ASCII after the service header.
    """
    blob = []
    for line in lines:
        tokens = [t for t in line.replace(":", "").split() if len(t) == 2]
        if any(t == "49" for t in tokens):
            blob.extend(int(t, 16) for t in tokens)
    try:
        start = blob.index(0x49)
    except ValueError:
        return None
    # skip: 49, service echo, frame/count byte
    payload = blob[start + 3:]
    chars = "".join(chr(b) for b in payload if chr(b) in string.printable[:95])
    return chars.strip() or None


def get_vin(ecu):
    return _ascii_from_mode09(ecu.query("0902"), 0x02)


def get_calibration_id(ecu):
    return _ascii_from_mode09(ecu.query("0904"), 0x04)


def get_cvn(ecu):
    lines = ecu.query("0906")
    for line in lines:
        parts = line.split()
        if parts and parts[0] == "49":
            return " ".join(parts[3:])
    return None


def get_ecu_name(ecu):
    return _ascii_from_mode09(ecu.query("090A"), 0x0A)


def get_mil_status(ecu):
    b = data_bytes(ecu.query("0101"), "41")
    if not b or len(b) < 2:
        return None
    return {"mil_on": bool(b[1] & 0x80), "dtc_count": b[1] & 0x7F}


def supported_pids(ecu):
    """Query PID-support bitmaps (0100, 0120, ... 01A0)."""
    supported = []
    for base in range(0x00, 0xC0, 0x20):
        b = data_bytes(ecu.query(f"01{base:02X}"), "41")
        if not b or len(b) < 5:
            break
        for i, byte in enumerate(b[1:5]):
            for bit in range(8):
                if byte & (0x80 >> bit):
                    supported.append(base + i * 8 + bit + 1)
        if not (b[4] & 0x01):  # next range not supported
            break
    return supported
