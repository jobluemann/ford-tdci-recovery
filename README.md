# ford-tdci-recovery

Backup-first recovery diagnostics for **Ford 2.0 TDCi** vehicles (Kuga Mk2,
Focus Mk3 and related) after a **battery replacement or module power loss** —
the known condition where the PCM loses its adaptations and the car drives
"laggy" with faults it never had before.

Runs on **Windows (portable, no admin install)** and **Linux Mint**, over an
**ELM327 adapter via USB or Bluetooth**. One Python file to launch, one
dependency (`pyserial`).

## What it does

- **Backup before anything else** — snapshots all readable vehicle state
  (VIN, calibration ID, CVN, ECU name, MIL/readiness, supported-PID map,
  stored fault codes, raw DPF-pressure sample) to a timestamped JSON file.
  Clearing codes is refused until a backup exists in the session.
- **Fault-code decoding** with Ford DPF-specific descriptions
  (P2002, P2452–P2455, P2463, P246C, P242F, plus post-battery U/P codes).
- **Live DPF differential pressure** readout (Mode-22 PID is configurable).
- **Post-battery recovery checklist** — BMS reset (including the manual
  high-beam/brake-pedal method), idle/throttle relearn, steering-angle
  reset, and DPF learned-value reset guidance. See
  `docs/POST_BATTERY_PROCEDURE.md`.
- **Raw command mode** for any custom PID.

## What it deliberately does not do

- No sensor emulation, signal spoofing, or DPF "override". A generic ELM327
  cannot inject analog sensor signals at all, and emissions defeat is
  illegal for road vehicles. This tool exists to *fix the actual fault*.
- No seed/key security access. PATS keys, module As-Built blocks and
  learned-value reset routines are Ford-proprietary — use
  [FORScan](https://forscan.org) (free) alongside this tool for those.

## Install & run

```bash
pip install -r requirements.txt   # just pyserial
python ford_recovery.py --demo    # try it with a simulated ECU, no car needed
python ford_recovery.py           # real adapter: pick the port from the list
python ford_recovery.py --port COM5          # Windows, skip port selection
python ford_recovery.py --port /dev/rfcomm0  # Linux Mint Bluetooth
```

No admin rights are needed to run it on Windows — any Python 3.8+ works,
including the portable/embeddable distribution.

## Bluetooth setup

**Windows:** pair the adapter (PIN usually `1234` or `0000`), then check
*Bluetooth settings → More Bluetooth options → COM ports* for the **outgoing**
COM port. Pass it with `--port`.

**Linux Mint:**
```bash
bluetoothctl pair <MAC> && bluetoothctl trust <MAC>
sudo rfcomm bind 0 <MAC>        # one-time, needs sudo for the bind itself
python ford_recovery.py --port /dev/rfcomm0   # the app itself runs as user
```

**Android:** this project targets laptops. On Android, use *Car Scanner ELM*
(live data) or *FORScan Lite* (Ford service functions) with the same
Bluetooth adapter.

**Note for Ford-specific functions:** learned-value resets and forced
regeneration via FORScan need an ELM327 with an **HS/MS-CAN switch**; many
cheap Bluetooth adapters are HS-CAN only.

## Project layout

```
ford_recovery.py        entry point
ftr/elm327.py           ELM327 transport (USB/Bluetooth serial) + simulator
ftr/obd.py              DTC / VIN / Mode-09 / PID decoding
ftr/backup.py           full readable-state snapshot (JSON)
ftr/cli.py              interactive menu
docs/POST_BATTERY_PROCEDURE.md
backups/                your snapshots land here (git-ignored)
```

## License

MIT — see LICENSE. Use at your own risk; always snapshot before clearing.
