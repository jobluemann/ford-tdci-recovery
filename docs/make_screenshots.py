#!/usr/bin/env python3
"""Capture real screenshots of the running GUI for the README/showcase.

Launches the actual app against the simulated car, presses the real buttons,
asks the live AI one of the owner's real questions, and saves PNGs of the
window to docs/screenshots/. Run on Windows or Linux with a desktop:

    python docs/make_screenshots.py
"""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import ImageGrab

from ftr import aichat, aiconfig
from ftr.gui import DiagApp

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)

app = DiagApp(simulate=True)
app.geometry("1180x640+40+40")


def pump(seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.update()
        time.sleep(0.05)


def snap(name):
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h)).save(OUT / name)
    print("saved", name)


app.update()
pump(0.5)

# 1. connected, clean window
app.connect()
pump(0.5)
snap("01_main_connected.png")

# 2. fault codes + module scan
app.do_dtcs()
app.do_scan()
pump(7)
snap("02_fault_codes_module_scan.png")

# 3. live AI diagnosis of a real owner symptom (in a thread so the
#    window stays alive while Qwen thinks)
aiconfig.apply()
q = "gears scratch between 1 2 3 when shifting — known issue? most likely cause?"
result = {}


def ask():
    try:
        result["r"] = aichat.chat_grounded(q)
    except Exception as e:
        result["e"] = e


threading.Thread(target=ask, daemon=True).start()
t0 = time.time()
while not result and time.time() - t0 < 150:
    app.update()
    time.sleep(0.1)

app.log(f"AI question: {q}")
if "r" in result:
    reply, ev = result["r"]
    if ev:
        app.log("--- auto-gathered evidence ---")
        for line in ev.split("\n"):
            app.log(line)
        app.log("------------------------------")
    for line in ("ai> " + reply).split("\n"):
        app.log(line)
else:
    app.log(f"ai> (AI offline during capture: {result.get('e')})")
pump(1.0)
app.out.see("end")
app.update()
snap("03_ai_diagnosis.png")

app.destroy()
print("done — screenshots in", OUT)
