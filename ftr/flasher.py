"""PCM flash orchestration + scripted UDS simulator for testing.

FlashPlan is a plain dict (loaded from JSON) describing the ECU-specific
parameters — session subfunctions, security-access levels, erase/verify
routine IDs, transfer block size. Those values differ per ECU generation;
you supply them from your own documentation.

flash() performs:
  preflight voltage check -> extended session -> programming session ->
  security access (via caller-supplied key function) -> erase routine ->
  RequestDownload / TransferData loop with progress -> TransferExit ->
  verify routine -> ECU reset.

The caller MUST supply:
  key_fn(level: int, seed: bytes) -> bytes     (your seed/key algorithm)
  firmware blocks                              (parsed VBF or raw bin)

This module contains no manufacturer-proprietary material.
"""

import json
import time
from datetime import datetime

from .uds import UDSClient
from .vbf import summarize


class FlashAbort(Exception):
    pass


def load_plan(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def preflight_voltage(elm, minimum=12.2):
    resp = (elm.query("ATRV") or ["0"])[0].replace("V", "").strip()
    try:
        volts = float(resp)
    except ValueError:
        raise FlashAbort(f"Cannot read adapter voltage (got {resp!r})")
    if volts < minimum:
        raise FlashAbort(
            f"Supply voltage {volts} V is below {minimum} V. "
            "Connect a battery maintainer before flashing.")
    return volts


def identify(uds, dids=(0xF187, 0xF188, 0xF18C)):
    out = {}
    for did in dids:
        try:
            raw = uds.read_data_by_identifier(did)
            out[f"F{did:04X}"] = raw.decode(errors="replace").strip("\x00")
        except Exception as e:
            out[f"F{did:04X}"] = f"<unreadable: {e}>"
    return out


def flash(elm, plan, blocks, key_fn, log=print):
    uds = UDSClient(elm, plan.get("tx_id", "7E0"), plan.get("rx_id", "7E8"))
    volts = preflight_voltage(elm, plan.get("min_voltage", 12.2))
    log(f"Preflight: supply {volts} V OK")
    log(f"Firmware: {summarize(blocks)}")

    info = identify(uds)
    log(f"Module identity: {info}")

    log("Entering extended session...")
    uds.diagnostic_session(int(plan["session"]["extended"], 16))
    log("Entering programming session...")
    uds.diagnostic_session(int(plan["session"]["programming"], 16))
    uds.tester_present()

    for level in plan["security"]:
        seed_sub = int(level["seed_sub"], 16)
        key_sub = int(level["key_sub"], 16)
        seed = uds.security_access_seed(seed_sub)
        log(f"Security level 0x{seed_sub:02X}: seed {seed.hex().upper()}")
        key = key_fn(seed_sub, seed)
        uds.security_access_key(key_sub, key)
        log("  key accepted")

    erase_id = int(plan["erase_routine"], 16)
    log(f"Erasing (routine 0x{erase_id:04X})...")
    uds.routine_control(erase_id)

    total = sum(len(b) for b in blocks)
    sent = 0
    t0 = time.time()
    for block in blocks:
        max_block = uds.request_download(block.address, len(block),
                                         addr_len_fmt=int(plan.get("addr_len_fmt", "44"), 16))
        chunk = min(int(plan.get("block_size", 256)), max_block or 256)
        counter = 1
        for off in range(0, len(block), chunk):
            uds.transfer_data(counter, block.data[off:off + chunk])
            counter += 1
            sent = min(sent + chunk, total)
            pct = 100.0 * sent / total
            rate = sent / max(time.time() - t0, 0.001)
            log(f"  0x{block.address + off:08X}  {pct:5.1f}%  ({rate:,.0f} B/s)")
        uds.transfer_exit()
    log("All blocks transferred.")

    verify_id = plan.get("verify_routine")
    if verify_id:
        log(f"Verifying (routine 0x{int(verify_id, 16):04X})...")
        uds.routine_control(int(verify_id, 16))

    log("Resetting ECU...")
    uds.ecu_reset()
    log("Flash complete. Cycle ignition, then run a full backup snapshot and "
        "compare against the pre-flash JSON.")


# ---------------------------------------------------------------------------
# Scripted UDS-capable simulator for offline testing of the whole flow.
# ---------------------------------------------------------------------------

class SimulatedUDSECU:
    """Answers the UDS flashing conversation with scripted positives."""

    def __init__(self):
        self.written = bytearray()

    def query(self, cmd):
        toks = [t for t in cmd.replace("\r", " ").split() if len(t) in (2, 4)]
        if cmd.strip().upper().startswith("AT"):
            if cmd.strip().upper() == "ATRV":
                return ["13.4V"]
            return ["OK"]
        b = bytes(int(t, 16) for t in toks)
        sid, sub = b[0], b[1] if len(b) > 1 else 0
        if sid == 0x10:
            return [f"50 {sub:02X}"]
        if sid == 0x3E:
            return ["7E 00"]
        if sid == 0x22:
            did = (b[1] << 8) | b[2]
            name = {0xF187: b"AB12-14C046-AA", 0xF188: b"FV6112B565DA",
                    0xF18C: b"PCM_SID208"}.get(did, b"?")
            hexdata = " ".join(f"{c:02X}" for c in name)
            return [f"62 {b[1]:02X} {b[2]:02X} {hexdata}"]
        if sid == 0x27:
            if sub % 2 == 1:
                return [f"67 {sub:02X} AA BB CC DD"]
            return [f"67 {sub:02X}"]
        if sid == 0x31:
            return [f"71 {sub:02X} {b[2]:02X} {b[3]:02X}"]
        if sid == 0x34:
            return ["74 20 01 00"]          # maxNumberOfBlockLength = 0x0100
        if sid == 0x36:
            self.written.extend(b[2:])
            return [f"76 {sub:02X}"]
        if sid == 0x37:
            return ["77"]
        if sid == 0x11:
            return [f"51 {sub:02X}"]
        return ["7F", f"{sid:02X}", "11"]

    def close(self):
        pass


def demo_key_fn(level, seed):
    """Demo seed/key: NOT a real algorithm - just echoes a transformation."""
    return bytes((x ^ 0x5A) for x in seed)
