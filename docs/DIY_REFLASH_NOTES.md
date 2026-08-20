# DIY In-Vehicle Reflash — Notes, Limits, and What You Must Supply

`pcm_flasher.py` is a UDS (ISO 14229) flashing framework over ISO-TP via an
ELM327-class adapter. It ships with **no manufacturer-proprietary material**.
Three inputs must come from you:

## 1. The flash plan (`--config`)

Per-ECU parameters: CAN IDs, session subfunctions, security-access levels,
erase/verify routine IDs, address/length format, transfer block size. An
example skeleton is in `config/ford_sid20x_example.json`. Every value in it
is a placeholder — verify against documentation for your exact hardware part
number. A wrong erase routine ID or session sequence is how modules get
bricked.

## 2. The seed/key algorithm (`--seedkey`)

A Python module you write exposing:

```python
def compute_key(level: int, seed: bytes) -> bytes:
    ...
```

The PCM refuses all writes without passing security access. Given your
background with truck diagnostic tooling you know where this comes from; it
is deliberately not part of this repository.

## 3. The firmware file (`--file`)

- `.vbf` container — parsed automatically (header + addressed blocks)
- raw `.bin` — requires `--load-address 0x........`

## Hard safety rules (enforced or warned in code)

- **Wired adapter only.** The tool refuses to proceed unless you type WIRED;
  `--allow-bluetooth` exists only because you asked for BT support, but a
  dropped frame mid-erase is a bricked PCM. Do not use it on a vehicle you
  cannot recover on a bench.
- **Battery maintainer mandatory.** Preflight checks adapter-reported voltage
  (default minimum 12.4 V) and aborts below it. Use a maintainer holding
  ~13.5 V for the entire session.
- **Speed reality.** ELM327 at 38.4 kbaud moves roughly 1–2 kB/s of payload
  through ISO-TP with all overheads. A multi-MB calibration can take the
  better part of an hour. An STN-based adapter (OBDLink-class) at 500 kbaud
  is 10× faster and far more reliable; J-2534 hardware is better still.
- **Before flashing:** run `ford_recovery.py` menu option 1 so you have the
  module's identity (VIN, calibration, CVN) on record. After flashing, run it
  again and compare.

## Test offline first

```
python pcm_flasher.py --demo
```

flashes a synthetic 3 KB image into a scripted simulator exercising every
step: sessions, security access, erase, download, transfer loop, verify,
reset. Never point this at a car before the demo passes cleanly.
