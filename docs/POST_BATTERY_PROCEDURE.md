# Post-Battery-Replacement Recovery — Ford 2.0 TDCi (Kuga Mk2 / Focus Mk3)

After a battery disconnect or replacement, several modules lose learned
adaptations. The classic symptom set is laggy throttle response, unstable
idle, odd charging behaviour, and warning lights that were not there before.
Work through this list **in order** after taking a backup snapshot.

## 1. Battery Monitoring System (BMS) reset — do this first

Ford's BMS tracks battery age/state-of-charge. After fitting a new battery it
must be told, or it keeps "protecting" a battery that no longer exists —
under-charging, smart-charge weirdness, and lag.

**Manual method (works on most Kuga Mk2 / Focus Mk3):**

1. Ignition ON, engine OFF.
2. Within 10 seconds: flash the high beams **5 times**, then press and
   release the brake pedal **3 times**.
3. The battery warning lamp flashes **3 times** within ~15 seconds to confirm.

If the lamp does not flash, repeat with slightly faster inputs, or use
FORScan → service function **"Reset the battery monitoring system"**.

## 2. Idle / throttle relearn

1. Start the engine, all loads OFF (A/C, lights, heated screens).
2. Idle until fully warm (cooling fan cycles at least once).
3. Then idle 3 more minutes with A/C ON, then 3 minutes with A/C OFF.
4. Drive normally for 15–20 minutes including some gentle 2,500–3,000 rpm
   cruise so fuel trims and EGR adaptives rebuild.

## 3. Steering angle / ESP (if ESP or hill-assist warnings show)

With the engine running, turn the steering lock-to-lock twice, centre the
wheel, switch ignition off and on. The warning usually clears itself.

## 4. DPF pressure sensor learned values (only if DPF codes persist)

1. Read live DPF differential pressure with this tool (menu option 4):
   healthy is roughly 0–3 kPa at idle, rising smoothly with rpm.
2. If the reading is stuck at 0 or implausible with the engine running,
   inspect the two sensor hoses and the loom near the plug **before**
   assuming the sensor or DPF is dead (see dpf_failure_diagram.html).
3. After any hose/sensor repair: clear codes, then run
   **"Reset Differential Pressure Sensor Learned Values"** and
   **"Reset DPF Learned Values"** in FORScan — these are standard service
   functions, not an override.
4. If soot loading is genuinely high (P2463), perform a static/forced
   regeneration with FORScan, or a 20–30 minute sustained highway drive.

## What this tool backs up — and what it cannot

The backup snapshot captures everything readable through generic OBD:
VIN, calibration ID, CVN, ECU name, MIL/readiness state, supported-PID map,
stored fault codes and a raw DPF-pressure sample. Keep the JSON file — it is
your before/after proof.

**Not readable via generic ELM327** (Ford-proprietary security access):
PATS immobilizer keys, module As-Built/configuration blocks, and the learned-
value reset routines themselves. For those use FORScan (free; the extended
license covers PATS key work). This division is deliberate: the tool will
never attempt seed/key security access on your behalf.
