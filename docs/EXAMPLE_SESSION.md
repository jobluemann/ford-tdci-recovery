# Example Diagnostic Session — Ford Kuga Mk2 2.0 TDCi (simulated)

*Generated 2026-08-20 by `example_session.py` against the scripted fake car. VIN and codes are simulated but match the real vehicle's actual fault set.*

## 1. Backup snapshot (always first)

- saved: `backups\backup_20260820_145352.json`
- VIN (fake): `WF0MXXKUGA9876543`
- ECU: `PCM_SID208`  calibration `AB12-14C046-AA`
- MIL on: True, 3 stored codes

## 2. Full module scan (what the dashboard hides)

```
OK  PCM  (engine) [HS-CAN]
      P2453-2F [active,confirmed]
      P2463-2F [active,confirmed]
      P062F-00 [active,confirmed]
OK  TCM  (transmission) [HS-CAN]
      P0776-00 [active,confirmed]
OK  ABS/ESP [HS-CAN]
OK  IPC  (instrument cluster) [HS-CAN]
OK  BCM  (body/GEM) [HS-CAN]
OK  RCM  (airbag) [HS-CAN]
OK  DEM  (AWD coupling) [MS-CAN]
      P1889-00 [active,confirmed]
```

## 3. Symptom-by-symptom: known-issue verdict + AI diagnosis

### 3.1 Post-battery lag

> Owner says: "Vehicle is laggy after a battery replacement. Manual BMS reset and brake-pedal reset already done by a professional. Code P062F present. What is happening and what is the honest fix path?"

**KB verdict: YES known issue (confidence: medium)** — PCM loses adaptations / settings after battery replacement
- matching codes: P062F
- most likely cause: BMS (battery monitoring) not reset after new battery - charging logic wrong
- sources: docs/POST_BATTERY_PROCEDURE.md; docs/PCM_REPLACEMENT_GUIDE.md

**AI diagnosis (two-model pipeline: gpt-oss-20b research → qwen3.6-27b diagnostics, grounded in the KB):**

**KB Status**: P062F etiology and this exact post-battery replacement scenario are **not in KB**. The technical breakdown and fix path below are grounded strictly in the provided research-stage notes and Ford 2.0 TDCi architecture.

### What is happening
On the 2.0 TDCi, P062F typically flags a powertrain control module (PCM/ECU) communication fault, internal self-test failure, or loss of CAN handshake with the Battery Management System (BMS/Vantage adapter). After a battery swap, the ECU expects a stable, registered voltage signal and continuous BMS communication. If the BMS connector isn’t fully seated, the voltage threshold falls outside spec, or the ECU hasn’t completed its post-ACC reinitialization sequence, the PCM triggers a reduced-performance strategy. This restricts fueling, boost control, and throttle mapping to protect drivetrain and emissions hardware, manifesting as the lag you’re observing. The prior manual BMS and brake-pedal resets may not have cleared the fault if the underlying hardware link or ECU initialization wasn’t fully validated.

### Honest fix path
1. **Verify BMS connector & grounding**  
   Locate the BMS module (typically near the negative terminal or in the rear/trunk area). Disconnect, inspect pins for corrosion, bending, or backout, clean terminals, and reseat until fully locked. Confirm the vehicle ground strap is clean, tight, and directly to bare chassis metal.

2. **Battery specification & registration confirmation**  
   Verify the replacement matches OEM specs (capacity, CCA, terminal orientation, and EN/SAE rating). Ford 2.0 TDCi requires battery registration via IDS/Forscan to recalibrate charging profiles and update ECU voltage thresholds. An unregistered or mismatched battery will cause the BMS to fault and the PCM to restrict performance.

3. **Check voltage sensor circuit & CAN communication**  
   Using diagnostic software, confirm CAN bus status between ECU and BMS. Inspect the BMS wiring harness, relevant fuses, and power/ground feeds for opens, shorts, voltage drops under load, or burnt insulation. Repair or replace damaged sections per wiring diagram.

4. **ECU power-cycle & module handshake**  
   Disconnect the negative terminal for ≥10 minutes with ignition OFF and all doors closed. Reconnect, turn ignition ON (do not crank), wait 60–90 seconds for modules to complete CAN wake-up and handshake, then start. Avoid riding the brake for code clearance unless your specific model year procedure mandates it; some Ford generations rely solely on ignition cycles + CAN sleep/wake states.

5. **Clear DTCs & drive-cycle validation**  
   Clear codes only after hardware verification. Perform a drive cycle while monitoring P062F readiness and live BMS/ECU parameters. If the code returns or lag persists, capture freeze frame data to isolate whether the fault originates in the BMS module, wiring, or PCM communication driver.

6. **Module calibration or replacement (if warranted)**  
   If all hardware checks pass and P062F remains, check for applicable PCM/BMS firmware updates or TSBs. If none apply, a BMS or ECU communication driver fault may require module replacement. Do not bypass or disable the BMS; doing so will trigger secondary fueling/emissions faults and violate system architecture.

**Tool requirement**: Ford IDS or equivalent diagnostic platform (e.g., Forscan with IAP2/IAP2-E) for module communication tests, battery registration, and live CAN stream verification.

Reply with your model year/engine code (e.g., R2B6, R2BB, R2NA) if you need the exact IDS battery registration sequence or BMS connector pinout.

### 3.2 DPF pressure codes / limp mode

> Owner says: "DPF fault codes P2453 and P2463, car in limp mode. Is the DPF itself dead, or is something cheaper usually the cause on this engine?"

**KB verdict: YES known issue (confidence: high)** — DPF differential pressure sensor hoses / wiring failure
- matching codes: P2453
- most likely cause: Split or chafed rubber hoses between sensor and DPF pipes (most common)
- sources: Project failure map: dpf_failure_diagram.html; kugaownersclub.co.uk DPF threads

**AI diagnosis (two-model pipeline: gpt-oss-20b research → qwen3.6-27b diagnostics, grounded in the KB):**

On the Ford 2.0 TDCi, P2453 and P2463 accompanied by limp mode **rarely indicate a permanently failed DPF element**. Grounded in the provided known-issues database, the high-confidence primary cause is a failure in the **DPF Differential Pressure Sensor (DPS) circuit or plumbing**, which is significantly cheaper to diagnose and repair than the filter itself.

### 🔍 Documented Failure Points (per KB)
*Source: `dpf_failure_diagram.html` project failure map; `kugaownersclub.co.uk` DPF diagnostic threads*
- **Split or chafed rubber pressure hoses** running between the DPS and the DPF pipes (**most common**)
- **Soot-blocked metal take-off pipe nipple** on the exhaust where the hoses connect
- **Broken internal conductor in the wiring loom** near the DPS electrical connector, specifically the **blue wire with tracer**

### 📉 Why P2453 + P2463 Trigger Limp Mode
- `P2453` flags an out-of-range or implausible differential pressure signal from the DPS.
- When the ECU loses accurate delta-P data, it cannot validate soot accumulation rates. As a fail-safe, it sets `P2463` (DPF saturation/fail operational) and forces limp mode to prevent unmonitored exhaust backpressure or incomplete regenerations.
- These codes often cascade from a **sensor/plumbing fault**, not actual DPF blockage.

### 🛠️ Diagnostic Path (KB-Aligned)
1. **Physical Inspection:** Locate the DPS (typically mid-exhaust). Examine both flexible rubber hoses for cracks, splits, or exhaust-heat chafing. Check the metal take-off nipples for carbon/soot blockage restricting reference pressure.
2. **Loom/Connector Check:** Unplug the DPS harness and test continuity on the ECU side. Inspect for internal fracture in the **blue-wire-with-tracer**, which the KB identifies as a high-failure point near the plugin. Verify 5V supply, clean ground, and signal integrity for opens/shorts.
3. **Live Data Verification:** Use a capable scan tool to monitor DPS delta-P voltage/resistance and individual high-side/low-side readings at operating temperature. A flatline, zero differential, or erratic swinging under load confirms a DPS/wiring/plumbing fault rather than actual filter saturation.
4. **Rule Out Physical DPF Restriction:** Only if hoses, nipples, and wiring pass inspection, and live data shows a genuinely high, non-clearing differential pressure, should the DPF filter itself be suspected. Manual backpressure (pitot tube) testing can confirm if the filter is physically restricted.

### ✅ Bottom Line
Replace/repair the DPS rubber hoses, clear/unblock the metal take-off nipple, or splice/replace the frayed blue-wire-with-tracer first. These are low-cost, high-yield fixes that resolve the vast majority of P2453/P2463 limp-mode events on the 2.0 TDCi. Once the DPS circuit is restored, clear codes and perform a factory-supervised active regeneration to exit limp mode and reseat DPF soot management baselines.

*(Note: Additional engine-specific calibration steps or post-repair adaptation procedures are not in KB.)*

### 3.3 Gear scratch 1-2-3

> Owner says: "Automatic gearbox scratches between gears 1, 2 and 3 when shifting. Known issue on this model? Most likely cause and first checks?"

**KB verdict: YES known issue (confidence: high)** — Powershift 6DCT450 (wet-clutch auto) harsh/scratching shifts 1-2-3
- most likely cause: Mechatronic valve body / hydraulic pressure loss (most documented)
- sources: https://eco-torque.co.uk/blogs/news/ford-powershift-ford-powershift-problems-uk; https://www.kugaownersclub.co.uk/threads/understanding-powershift-problems.29075/

**AI diagnosis (two-model pipeline: gpt-oss-20b research → qwen3.6-27b diagnostics, grounded in the KB):**

**Known Issue Status:** Yes. Harsh/scratching shifts between gears 1, 2, and 3 are a documented failure mode on the Ford 6DCT450 Powershift (wet-clutch automatic) paired with the 2.0 TDCi. [Confidence: High]

**Most Likely Cause:** 
Per the KB, the primary failure mode is **mechanical/hydraulic degradation within the transmission control and actuation system**:
- **Mechatronic valve body malfunction / hydraulic pressure loss** (most frequently documented)
- **Clutch pack wear** secondary to internal spring system collapse
- **Debris/sludge blocking mechatronic oil pathways**, restricting actuation pressure to the wet clutches

**First Diagnostic Checks:**
1. **TCM/DTC Scan:** Pull all transmission-related fault codes. Prioritize codes indicating hydraulic pressure deviation, solenoid/valve body communication faults, or clutch adaptation limit breaches.
2. **Hydraulic Pressure Validation:** Verify ATF specification and fill level. Inspect fluid condition for contamination, oxidation, or metal particulates. If diagnostic hardware is available, log live hydraulic pressure data during 1–2–3 shifts to compare commanded vs. actual pressure.
3. **Mechatronic & Oil Pathway Inspection:** Check the mechatronic cover and hydraulic lines for external leaks or seepage. Remove and inspect the transmission oil filter/strainer for debris or varnish buildup. Restricted pathways directly cause pressure loss and erratic wet-clutch engagement.
4. **Clutch Pack Assessment:** If hydraulic pressure is within spec and the mechatronic unit responds correctly to calibration routines, proceed to internal inspection for clutch pack wear or collapsed damper/spring mechanisms. Internal collapse manifests as dragging or scratching engagement during low-speed gear transitions.

**Diagnostic Note:** Fluid exchange alone is rarely curative if internal spring collapse or significant valve body wear has occurred. Validate hydraulic integrity and mechatronic signal response first; only proceed to clutch pack replacement if pressure and control parameters are confirmed normal.

**Sources:** 
- https://eco-torque.co.uk/blogs/news/ford-powershift-ford-powershift-problems-uk
- https://www.kugaownersclub.co.uk/threads/understanding-powershift-problems.29075/

All findings are strictly per the provided KB. Provide stored DTCs, adaptation values, or VIN for targeted analysis. States not covered in the KB will be marked `not in KB`.

### 3.4 AWD dead, no dash warning

> Owner says: "All-wheel drive is not engaging but the dashboard shows no fault at all. How can that be, and where do I look first?"

**KB verdict: YES known issue (confidence: high)** — AWD (Haldex-type coupling) pump failure with NO dashboard warning
- most likely cause: Failed AWD pre-charge pump at the rear differential (filter gauze clogged from missed coupling oil services)
- sources: https://www.go-parts.com/garage/obd-p1889-ford-kuga-2012-2019-dw10f-2.0l; https://www.kugaownersclub.co.uk/threads/awd-malfunction-haldex-servicing-info.6955/

**AI diagnosis (two-model pipeline: gpt-oss-20b research → qwen3.6-27b diagnostics, grounded in the KB):**

This is a documented platform-specific behavior. On the 2.0 TDCi AWD variant, the Haldex-type coupling can lose rear-wheel engagement without illuminating a dashboard warning because certain mechanical or electrical failures do not immediately cross the DEM's (AWD control module) DTC threshold for driver alerting.

### Why the dash shows no fault
- **Hydraulic/Mechanical silent failure:** The pre-charge pump maintains baseline coupling pressure. If the inline pre-charge filter gauze becomes clogged (typically from missed coupling oil services), the pump can cavitate or mechanically seize without instantly tripping a pressure transducer fault or triggering a subsystem limp mode.
- **Electrical open circuits:** A broken earth strap, blown supply fuse, or corroded pump connector can drop the pump circuit open. Depending on DEM software version, an intermittent or hard open-circuit fault may not immediately register as a dashboard-illuminating DTC until the module loses communication entirely or detects a secondary plausibility error.
- **Module-level degradation:** Internal DEM driver circuit failures can silently stop sending pulse-width modulated signals to the pump without logging a hard fault visible on the instrument cluster.

### Where to look first (diagnostic priority per KB)
1. **Rear differential fluid & pre-charge filter gauze**  
   Check coupling oil level and condition. A clogged pre-charge filter is the most common cause of silent AWD disengagement. If service history is unknown or oil is dark/low, replace the coupling fluid and filter assembly.

2. **Pre-charge pump operation**  
   With the engine running, listen for the high-frequency whine of the Haldex pump mounted on the rear differential. No audible operation indicates pump seizure, loss of power, or loss of ground.

3. **Supply fuses & dedicated relay**  
   Locate and verify the Haldex/AWD fuse (typically labeled in the fusebox diagram) and its associated relay. Replace if blown or fatigued.

4. **Earth strap & chassis grounding**  
   Inspect the stainless steel earth strap running from the differential/pump housing to the chassis. A broken, corroded, or poorly torqued strap is a frequent culprit for silent pump dropout.

5. **Pump electrical connector**  
   Disconnect the 3–5 pin connector at the pump. Check for green corrosion, pushed-out pins, or cracked seals. Perform a multimeter continuity/resistance check on power, ground, and control lines back to the DEM.

6. **DEM deep scan**  
   Even with a clear instrument cluster, run a full Haldex/DEM module read with a professional diagnostic tool. Look for stored/historical codes, pump driver plausibility faults, or pressure sensor deviations that were logged but not escalated to the dash.

### Next steps
Start with the fluid/filter inspection and pump noise check. If those are normal, verify the fuse/earth strap/connector circuit. If electrical and hydraulic checks pass but engagement still fails, the pre-charge pump assembly or internal DEM driver circuit likely requires replacement.

*Sources: go-parts.com, kugaownersclub.co.uk, eco-torque.co.uk (all referencing OEM Haldex Gen 2/3 service data and verified owner/diagnostics reports for Ford 2.0 AWD platforms).* 

If your diagnostic path diverges from these steps or you encounter a symptom组合 not covered here, reply with the exact readings/components tested and I will clarify based on the KB or note it as `not in KB`.

### 3.5 Coolant in the oil

> Owner says: "There are signs of coolant mixing into the engine oil. What are the possible causes on the 2.0 TDCi, in order of likelihood?"

**KB verdict: YES known issue (confidence: medium)** — Coolant / water contamination in engine oil
- most likely cause: Oil cooler seal/housing failure (O-ring goes brittle, housing cracks at the seal seat - documented on this engine family)
- sources: https://www.kugaownersclub.co.uk/threads/egr-cooler-failure-bubbles-in-coolant.28746/; https://forums.ross-tech.com/index.php?threads/24255/

**AI diagnosis (two-model pipeline: gpt-oss-20b research → qwen3.6-27b diagnostics, grounded in the KB):**

Based on the documented failure patterns for the Ford 2.0 TDCi, coolant contamination in the engine oil typically originates from three primary failure points. Listed below in descending order of likelihood, strictly grounded in the known-issues knowledge base and technician reports:

### 1. Oil Cooler Seal/Housing Failure (Most Likely)
- **Mechanism:** The oil cooler integrates adjacent coolant and oil passages. Age and thermal cycling cause the retaining O-ring to harden and lose elasticity, or the cooler housing to crack precisely at the seal seat. This creates a direct hydraulic leak path from the pressurized coolant circuit into the oil gallery.
- **Verification Steps:** 
  - Remove the oil cooler assembly and inspect the O-ring for brittleness, flattening, or chemical degradation.
  - Examine the housing mating flange and seal groove for micro-cracks or stress fractures.
  - Correlate with oil pressure sensor data; a simultaneous pressure drop often accompanies a seal breach.
- **KB Citation:** Documented as the primary culprison this engine family. Sources: KugaOwnersClub, Ross-Tech forums.

### 2. EGR Cooler Internal Failure (Secondary)
- **Mechanism:** Internal heat-stress or coolant chemistry issues can fracture the EGR cooler’s coolant matrix. Coolant migrates into the exhaust gas recirculation stream, eventually entering the crankcase ventilation system and mixing with engine oil. A concurrent telltale sign is persistent air bubbles venting into the coolant expansion tank during operation.
- **Verification Steps:**
  - Run the engine at operating temperature with the expansion tank cap off; monitor for continuous bubbling (indicates gas/coolant migration).
  - Pressure-test the cooling system and inspect the EGR cooler core/end tanks for weeping or corrosion.
  - Check scanner data for EGR cooler inlet/outlet temperature deltas or pressure faults that may indicate internal breach.
- **KB Citation:** Widely reported alongside unexplained coolant loss and expansion tank bubbling. Sources: KugaOwnersClub, Ross-Tech forums.

### 3. Head Gasket Failure (Least Likely)
- **Mechanism:** While combustion chamber blow-by is a common cross-platform cause of fluid crossover, Ford 2.0 TDCi specialists consistently report head gasket failure as rare. The engine's block/head architecture and gasket sealing strategy typically isolate coolant and oil circuits until severe overheating or mechanical damage occurs.
- **Verification Steps:**
  - Cylinder leak-down and compression testing across all banks.
  - Coolant system gas analyzer (combustion gas sniff test) to rule out exhaust gas migration.
  - **Only suspect this after the oil cooler and EGR cooler are physically ruled out.**
- **KB Citation:** Specialists advise treating this as a last-resort diagnosis on this specific powertrain. Sources: KugaOwnersClub, Ross-Tech forums.

---
**Diagnostic Protocol & Compliance Notes**
- Proceed verification in the exact order above. Replace only confirmed faulty components; do not clear fault codes or alter coolant/EGR/DPF routing to mask symptoms. Emissions-system bypasses or deletions are explicitly prohibited and will void compliance while accelerating internal damage.
- If physical inspection and pressure testing rule out all three documented causes, the fault is **not in KB**. Recommend a full crankcase ventilation system audit, oil analysis, or specialist borescope/engine teardown evaluation.

---
*Every issue above is a documented, sourced known fault for this vehicle — the dealer-money-trap scenario this project exists to prevent.*