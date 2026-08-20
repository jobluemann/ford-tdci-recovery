# PCM Replacement & Reprogramming Guide — Ford Kuga Mk2 / Focus Mk3 2.0 TDCi

For the case where the PCM has genuinely lost its stored settings, refuses to
hold adaptations after correct resets (BMS reset, idle relearn, learned-value
resets all performed), and shows EEPROM/flash fault codes such as **P062F**
(internal control module EEPROM error) or **U0300** (software incompatibility).
At that point the module itself is the fault and the fix is replacement or
cloning — no sensor, hose, or reset procedure will cure failed flash memory.

---

## 0. Spend one hour ruling this out first (do NOT skip)

Before buying a module, eliminate the two things that mimic a dead PCM:

1. **Shared 5 V reference rail.** The PCM feeds one 5 V reference to several
   sensors (MAP, EGR position, fuel rail pressure, DPF pressure sensor,
   accelerator pedal). If ANY one of them shorts internally, it drags the rail
   down and the PCM looks "corrupt": multiple implausible sensor codes,
   adaptations that won't stick, lag.
   - Check: measure 5 V at the DPF sensor plug (key on). If it reads low
     (e.g. 1–3 V), unplug sensors on the rail one at a time until it recovers
     to 5 V — the last one unplugged is the culprit, and it costs a fraction
     of a PCM.
2. **Power and ground integrity.** Corroded PCM ground points and a tired new
   battery (or a bad earth strap after the battery swap) cause exactly this
   symptom set. Voltage-drop test the grounds under load.

If the rail is 5 V, grounds are clean, and P062F/U0300 persist → the PCM is
the fault. Proceed.

---

## 1. Identify the exact module

Everything downstream depends on an exact match. Record ALL of:

- **Hardware part number** on the PCM label (format like
  `AV61-12A650-XX` / `FV61-12B565-XX` — varies by year and market)
- **Calibration / tear-tag code** (e.g. the `AB12-14C046-AA` style ID your
  backup snapshot reads via Mode 09)
- **Engine code & power output** (2.0 TDCi came in ~115/140/150/163 PS;
  the ECU family is typically Siemens/Continental SID206/SID208/SID209)
- **Transmission** — manual vs. Powershift automatic use different software
- **VIN** — Ford's ETIS / Motorcraft As-Built lookup is keyed to it

Run a backup snapshot with this tool (menu option 1) **before** unplugging
anything — it captures VIN, calibration ID, CVN and ECU name into JSON, which
is exactly what the programming step needs later.

## 2. Choose one of three routes

| Route | Cost | What happens |
|---|---|---|
| **A. ECU cloning service** (recommended) | lowest | A specialist images your original PCM (flash + EEPROM) onto a donor unit. PATS, injector codes, As-Built all carry over. Plug in and drive. |
| **B. Used donor PCM + DIY programming** | medium | Cheapest hardware, but you must program PATS, As-Built and injector codes yourself (FORScan extended license / FJDS). |
| **C. New PCM from Ford + FDRS** | highest | Dealer programs a blank module to your VIN. Most expensive, fewest unknowns. |

Route A works even if the original PCM is half-dead — specialists can usually
read a failing EEPROM directly on the bench. Ask specifically for a
**"full clone including EEPROM"**, not just a flash copy.

For routes B and C the donor hardware part number MUST match; the calibration
can be reprogrammed, the hardware revision cannot.

## 3. What must be programmed after fitting (routes B & C)

In this order:

1. **Stable power.** Connect a battery maintainer/charger holding ~13.5 V.
   A voltage dip mid-flash bricks the new module. (Yes — the same power
   stability whose absence started this whole problem.)
2. **PATS immobilizer pairing.** The PCM must be introduced to the
   BCM/instrument cluster or the engine will crank and never start.
   FORScan (extended license) → PATS programming, or the incode/outcode
   procedure. Requires ~10 minute security wait per attempt.
3. **As-Built data.** Download the As-Built block for your VIN from Ford
   (ETIS / Motorcraft service site) and write it with FORScan. This is the
   module's configuration record — what the original lost.
4. **Injector correction codes (IMA/IQA).** Each injector's code is printed
   on its body and stored in the PCM. Read them from the old PCM first if it
   still communicates (FORScan shows them); otherwise read them physically
   off the injectors. Wrong or missing codes = rough idle, smoke, lag.
5. **Service resets.** DPF differential pressure sensor learned values, DPF
   learned values, then **BMS reset** (battery was disconnected again), then
   idle/throttle relearn — the full sequence in
   `docs/POST_BATTERY_PROCEDURE.md`.
6. **Verify.** Re-run this tool's backup snapshot and compare against the
   pre-replacement JSON: same VIN/calibration, MIL off, zero stored codes,
   DPF pressure ~0–3 kPa at idle.

## 4. Sourcing a donor / cloner

- Donor: match the hardware part number exactly; avoid flood/accident
  vehicles; ask for the donor's VIN so its history is checkable.
- Cloning services: established ECU specialists (e.g. ECU Testing,
  BBA-Reman internationally; local auto-electricians with bench-flash
  capability in SA). Confirm they support your SID-generation ECU before
  sending anything.
- Ship BOTH modules when cloning (original + donor).

## 5. Cautions

- Never interrupt a flash or PATS session — maintain power throughout.
- Do not clear codes on the new module before its own backup snapshot.
- If the car still lags with a known-good programmed PCM, the fault is
  upstream: wiring loom (chafed CAN or sensor harness) or a sensor pulling
  the 5 V rail down intermittently — back to section 0 with a scope.

## 6. Evidence trail

Keep: the pre-replacement backup JSON, the donor's part-number photo, the
As-Built file you wrote, and the post-replacement JSON. If the car is ever
inspected or sold, this file proves the emissions configuration is intact and
VIN-correct — something a sensor bypass could never show.
