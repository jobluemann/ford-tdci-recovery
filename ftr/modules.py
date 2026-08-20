"""Ford module map and full-vehicle module scan over ELM327.

Reads presence + UDS fault codes (service 0x19 0x02 0xAF) from each module.
Reading requires no security access — this is the 'open' half of diagnostics.

Bus notes: powertrain modules sit on HS-CAN (500k). Body modules and often
the DEM (AWD) sit on MS-CAN (125k) — your ELM327 needs an HS/MS-CAN switch
to see them. Modules on the other bus show as 'not reachable (bus?)'.
"""

import time

FORD_MODULES = [
    {"name": "PCM  (engine)",            "tx": "7E0", "rx": "7E8", "bus": "HS"},
    {"name": "TCM  (transmission)",      "tx": "7E1", "rx": "7E9", "bus": "HS"},
    {"name": "ABS/ESP",                  "tx": "760", "rx": "768", "bus": "HS"},
    {"name": "IPC  (instrument cluster)","tx": "720", "rx": "728", "bus": "HS"},
    {"name": "BCM  (body/GEM)",          "tx": "726", "rx": "72E", "bus": "HS"},
    {"name": "RCM  (airbag)",            "tx": "737", "rx": "73F", "bus": "HS"},
    {"name": "DEM  (AWD coupling)",      "tx": "761", "rx": "769", "bus": "MS"},
]

_SYS = "PCBU"


def decode_uds_dtcs(lines):
    """Decode 0x19 0x02 response lines into ['P2453-2F', ...] style strings."""
    toks = []
    for ln in lines:
        parts = [t for t in ln.split() if len(t) == 2]
        if parts and parts[0] == "59":
            toks.extend(parts)
    if not toks:
        return []
    try:
        data = [int(t, 16) for t in toks]
    except ValueError:
        return []
    # skip 59 02 <status-mask>
    payload = data[3:]
    out = []
    for i in range(0, len(payload) - 3, 4):
        b1, b2, b3, status = payload[i:i + 4]
        if b1 == 0 and b2 == 0 and b3 == 0:
            continue
        code = f"{_SYS[(b1 >> 6) & 3]}{(b1 >> 4) & 3}{b1 & 0xF:X}{b2:02X}-{b3:02X}"
        flags = []
        if status & 0x01:
            flags.append("active")
        if status & 0x08:
            flags.append("confirmed")
        if status & 0x20:
            flags.append("not-since-clear")
        out.append(f"{code} [{','.join(flags) or f'status=0x{status:02X}'}]")
    return out


def probe_module(elm, mod, settle=0.08):
    elm.query(f"AT SH {mod['tx']}")
    elm.query(f"AT CRA {mod['rx']}")
    elm.query("ATH0")
    time.sleep(settle)
    present = bool(elm.query("3E 00"))
    dtcs = decode_uds_dtcs(elm.query("19 02 AF")) if present else []
    return present, dtcs


def scan_modules(elm, log=print):
    """Probe every known Ford module. Returns {name: (present, [dtcs])}."""
    results = {}
    for mod in FORD_MODULES:
        try:
            present, dtcs = probe_module(elm, mod)
        except Exception as e:
            present, dtcs = False, [f"<error: {e}>"]
        results[mod["name"]] = (present, dtcs)
        tag = "OK " if present else ("BUS?" if mod["bus"] == "MS" else "---")
        log(f"{tag} {mod['name']} [{mod['bus']}-CAN]")
        for d in dtcs:
            log(f"      {d}")
    return results


class SimulatedVehicle:
    """Whole-vehicle simulator: answers per-module probes by tracking AT SH."""

    SCRIPT = {
        "7E0": ["59 02 FF 24 53 2F 09"],            # PCM: P2453-2F active+confirmed
        "7E1": ["59 02 FF"],                        # TCM: no faults
        "760": ["59 02 FF"],
        "720": ["59 02 FF"],
        "726": ["59 02 FF 81 89 00 09"],            # BCM: B0189-00 active+confirmed
        "737": ["59 02 FF"],
        # 761 (DEM) deliberately silent -> demonstrates MS-CAN 'not reachable'
    }

    def __init__(self):
        self.header = None

    def query(self, cmd):
        c = cmd.strip().upper()
        if c.startswith("AT"):
            if c.startswith("AT SH"):
                self.header = c.split()[-1]
            return ["OK"]
        if self.header not in self.SCRIPT:
            return [] if c == "3E 00" else ["NO DATA"]
        if c == "3E 00":
            return ["7E 00"]
        if c == "19 02 AF":
            return self.SCRIPT[self.header]
        return ["NO DATA"]

    def close(self):
        pass
