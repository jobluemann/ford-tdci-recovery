#!/usr/bin/env python3
"""Headless GUI smoke test: drives the real buttons against the fake car."""

import time

from ftr.gui import DiagApp

app = DiagApp(simulate=True)
app.withdraw()  # don't actually show the window during the test

app.connect()
assert app.ecu is not None, "simulation connect failed"

# press every button
app.do_backup()
app.do_dtcs()
app.do_scan()
app.do_live()

# let worker threads run, pumping tk events
t0 = time.time()
while time.time() - t0 < 6:
    app.update()
    time.sleep(0.05)
app.do_live()  # stop live mode
time.sleep(0.3)
app.update()

text = app.out.get("1.0", "end")
app.destroy()

required = [
    "simulated vehicle",
    "Backup saved:",
    "PCM_SID",            # ECU name in backup
    "P2453",              # decoded DTC
    "P2463",
    "OK  PCM",            # module scan
    "BUS? DEM",           # MS-CAN demonstration
    "raw=300",            # live DPF sample (0x012C = 300)
]
missing = [r for r in required if r not in text]
if missing:
    print("GUI TEST FAILED, missing:", missing)
    print(text[-2000:])
    raise SystemExit(1)
print("GUI SIMULATION TEST PASSED — all buttons worked against the fake car")
