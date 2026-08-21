# Adapter guide — what to buy, what to avoid, bulk criteria

Everything here applies to Ford 2.0 TDCi diagnostics with this suite (and
FORScan alongside it). Prices fluctuate; treat them as rough tiers, not quotes.

## The one requirement that actually matters: HS/MS-CAN

Ford splits modules across two CAN buses:

- **HS-CAN** (engine/PCM, gearbox/TCM, ABS, cluster) — *every* ELM327 can see these
- **MS-CAN** (body/GEM, **AWD coupling (DEM)**, audio, parking) — needs an adapter
  with a physical **HS/MS-CAN switch** or automatic switching

The silent AWD fault (P1889 in the DEM) lives on MS-CAN. An HS-CAN-only
adapter shows `BUS?` for that module — which is exactly why this fault
survives unnoticed for years. **For this project, buy adapters with the
switch.**

## Adapter tiers

| Tier | Examples | Works with suite | Notes |
|---|---|---|---|
| **Best (bulk-worthy)** | vLinker FS/FD USB or BT, ELS27 (USB) | everything incl. MS-CAN | STN chip, fast, reliable, HS/MS-CAN auto or switch. The bulk-buy candidate. |
| **Good** | OBDLink EX (USB) | everything | Premium price, excellent firmware |
| **Budget OK** | ELM327 **v1.4/v1.5** Bluetooth (classic SPP) | HS-CAN diagnostics, KB, AI, live DPF | No MS-CAN. Fine for PCM/TCM work — most of this suite |
| **Avoid** | anything claiming **ELM327 "v2.1"** | unreliable | Real ELM327 never shipped v2.1 — these are gutted clones with commands missing; expect timeouts and garbage |

## USB vs Bluetooth classic vs BLE

| Form | Pros | Cons |
|---|---|---|
| **USB cable** | fastest, most stable, required for reflashing | laptop only |
| **Bluetooth classic (SPP)** | cheap, works with this app on Mint + Windows | pairing quirks; no iPhone |
| **BLE** | works from the PWA in Chrome/Edge via Web Bluetooth | slower; no SPP → desktop app can't use it; iPhone still needs a native app |

**Recommendation:** standardise on **vLinker FS-style USB** for the workshop
kit and **v1.4+ Bluetooth classic** for owners. BLE only if you specifically
want the browser-based phone path.

## Bulk-buy checklist (for bundling with the software)

1. STN2120/STN11xx or genuine ELM327 v1.4+ chipset — ask the supplier directly
2. HS/MS-CAN switching (physical switch or auto)
3. 500 kbit CAN support (Ford HS-CAN) — all above have it
4. Order 2 samples first; run `python ford_recovery.py --demo` then a real
   car scan and the full module scan before committing to a batch
5. Firmware must accept standard AT commands (this suite uses ATZ/ATE0/ATL0/
   ATS0/ATH1/ATSP0 + modes 01/03/09/19/22)

## What about a Raspberry Pi?

See `docs/RASPBERRY_PI.md` — the Pi becomes a permanently-plugged diagnostics
hub: adapter on the car, Pi serves the phone app over WiFi. No screen needed.
