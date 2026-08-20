"""Minimal UDS (ISO 14229) client over an ELM327 transport.

The ELM327 handles ISO-TP (15765-2) segmentation/reassembly internally for
CAN protocols, so this layer works in service payloads only. Addressing is
configured with AT SH / AT CRA; headers are switched off so responses arrive
as pure payload bytes.

Designed for both ELM327 (real) and the scripted simulator (testing).
"""

import time


class UDSNRC(Exception):
    """Negative response from the ECU."""

    NAMES = {
        0x10: "generalReject", 0x11: "serviceNotSupported",
        0x12: "subFunctionNotSupported", 0x13: "incorrectMessageLength",
        0x22: "conditionsNotCorrect", 0x24: "requestSequenceError",
        0x31: "requestOutOfRange", 0x33: "securityAccessDenied",
        0x35: "invalidKey", 0x36: "exceededNumberOfAttempts",
        0x37: "requiredTimeDelayNotExpired", 0x70: "uploadDownloadNotAccepted",
        0x71: "transferDataSuspended", 0x72: "generalProgrammingFailure",
        0x73: "wrongBlockSequenceCounter", 0x78: "responsePending",
        0x7E: "subFunctionNotSupportedInActiveSession",
        0x7F: "serviceNotSupportedInActiveSession",
        0x92: "voltageTooLow", 0x93: "voltageTooHigh",
    }

    def __init__(self, service, nrc):
        self.service, self.nrc = service, nrc
        super().__init__(f"NRC 0x{nrc:02X} ({self.NAMES.get(nrc, '?')}) on service 0x{service:02X}")


class UDSTimeout(Exception):
    pass


class UDSClient:
    def __init__(self, elm, tx_id="7E0", rx_id="7E8", settle=0.05):
        self.elm = elm
        for cmd in (f"AT SH {tx_id}", f"AT CRA {rx_id}", "AT AT1",
                    "AT ST 64", "ATH0", "ATAL"):
            elm.query(cmd)
            time.sleep(settle)

    # ------------------------------------------------------------------
    def _exchange(self, payload: bytes, pending_retries=12) -> bytes:
        cmd = " ".join(f"{b:02X}" for b in payload)
        for _ in range(pending_retries):
            lines = self.elm.query(cmd)
            toks = [t for ln in lines for t in ln.split() if len(t) == 2]
            if not toks:
                raise UDSTimeout(f"No response to {cmd}")
            data = bytes(int(t, 16) for t in toks)
            if data[0] == 0x7F:
                if len(data) > 2 and data[2] == 0x78:   # responsePending
                    time.sleep(0.5)
                    continue
                raise UDSNRC(data[1], data[2] if len(data) > 2 else 0)
            return data
        raise UDSTimeout("ECU kept answering responsePending (NRC 0x78)")

    @staticmethod
    def _expect(data: bytes, service: int) -> bytes:
        """Check positive-response SID (service + 0x40), return the rest."""
        if not data or data[0] != service + 0x40:
            raise UDSNRC(service, data[1] if len(data) > 1 else 0)
        return data[1:]

    # ------------------------- UDS services ----------------------------
    def read_data_by_identifier(self, did: int) -> bytes:
        r = self._exchange(bytes((0x22, (did >> 8) & 0xFF, did & 0xFF)))
        return self._expect(r, 0x22)[2:]          # strip echoed DID

    def diagnostic_session(self, sub: int) -> bytes:
        return self._expect(self._exchange(bytes((0x10, sub))), 0x10)

    def security_access_seed(self, sub: int) -> bytes:
        r = self._expect(self._exchange(bytes((0x27, sub))), 0x27)
        return r[1:]                               # strip echoed sub-fn

    def security_access_key(self, sub: int, key: bytes) -> bytes:
        return self._expect(self._exchange(bytes((0x27, sub)) + key), 0x27)

    def routine_control(self, routine_id: int, sub: int = 0x01, data: bytes = b"") -> bytes:
        r = self._exchange(bytes((0x31, sub, (routine_id >> 8) & 0xFF,
                                  routine_id & 0xFF)) + data)
        return self._expect(r, 0x31)[3:]           # strip sub + echoed RID

    def request_download(self, address: int, length: int,
                         data_format: int = 0x00, addr_len_fmt: int = 0x44):
        """Returns maxNumberOfBlockLength reported by the ECU."""
        addr = address.to_bytes(4, "big")
        size = length.to_bytes(4, "big")
        r = self._exchange(bytes((0x34, data_format, addr_len_fmt)) + addr + size)
        body = self._expect(r, 0x34)
        len_fmt = body[0] >> 4
        return int.from_bytes(body[1:1 + len_fmt], "big")

    def transfer_data(self, block_counter: int, data: bytes) -> None:
        self._expect(self._exchange(bytes((0x36, block_counter & 0xFF)) + data), 0x36)

    def transfer_exit(self) -> bytes:
        return self._expect(self._exchange(bytes((0x37,))), 0x37)

    def ecu_reset(self, sub: int = 0x01) -> bytes:
        return self._expect(self._exchange(bytes((0x11, sub))), 0x11)

    def tester_present(self) -> None:
        self._exchange(bytes((0x3E, 0x00)))
