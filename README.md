# ford-tdci-recovery

[![demo-test](https://github.com/jobluemann/ford-tdci-recovery/actions/workflows/test.yml/badge.svg)](https://github.com/jobluemann/ford-tdci-recovery/actions/workflows/test.yml)

Backup-first **open-source diagnostic suite** for **Ford 2.0 TDCi** vehicles
(Kuga Mk2, Focus Mk3 and platform relatives). Born from the known condition
where the PCM loses its adaptations after a **battery replacement** — now
grown into a full-vehicle tool with a curated, sourced **known-issues
knowledge base**, so owners stop paying dealer diagnostic fees to rediscover
faults that are already documented as standard problems on their model.

Runs on **Windows (portable, no admin install)** and **Linux Mint**, over an
**ELM327 adapter via USB or Bluetooth**. One Python file to launch, one
dependency (`pyserial`). See `docs/ARCHITECTURE.md` for the vision.

## Suite features (v0.2)

- **Backup before anything else** — snapshots all readable vehicle state to
  timestamped JSON; clearing codes is refused until a backup exists.
- **Fault-code decoding** with Ford DPF-specific descriptions.
- **Full module scan** — PCM, TCM, ABS/ESP, cluster, BCM, airbag, and the
  DEM (AWD) module, with per-module UDS fault codes the dashboard never
  shows. (MS-CAN modules need an adapter with an HS/MS-CAN switch.)
- **Known-issues lookup** — your DTCs + plain-English symptoms are ranked
  against a curated KB (Powershift 6DCT450 harsh shifts, silent AWD pump
  failure, coolant-in-oil paths, DPF sensor circuit, and more), every entry
  marked `yes/no known issue` with confidence, ranked causes, checks and
  **source links**.
- **Forum/RSS symptom search** across your configured feeds, with offline
  cache.
- **Optional AI assistant** (any OpenAI-compatible endpoint, VIN stripped).
- **Community data platform** — `site/` drops onto any PHP host (no Node):
  anonymized opt-in reports power a shared fault database.
- **Live DPF differential pressure** readout with CSV logging.
- **Expert UDS reflash framework** (`pcm_flasher.py`) — bring your own
  seed/key and firmware; wired-only guardrails.

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
ford_recovery.py        entry point (diagnostics/backup)
pcm_flasher.py          expert UDS reflash entry point (you supply seed/key + firmware)
ftr/elm327.py           ELM327 transport (USB/Bluetooth serial) + simulator
ftr/obd.py              DTC / VIN / Mode-09 / PID decoding
ftr/backup.py           full readable-state snapshot (JSON)
ftr/cli.py              interactive menu
ftr/uds.py              UDS (ISO 14229) client over ELM327
ftr/vbf.py              VBF firmware container parser
ftr/flasher.py          flash orchestration + scripted simulator
config/                 flash plan skeletons (placeholder values — verify!)
docs/POST_BATTERY_PROCEDURE.md
docs/PCM_REPLACEMENT_GUIDE.md   when the module itself has failed
docs/DIY_REFLASH_NOTES.md       expert in-vehicle reflash: inputs & safety
backups/                your snapshots land here (git-ignored)
```

## License

MIT — see LICENSE. Use at your own risk; always snapshot before clearing.
