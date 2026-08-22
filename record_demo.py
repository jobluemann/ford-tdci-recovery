"""Record a scripted simulation session as an animated GIF.

Drives the real GUI (fake car), captures frames with PIL, saves
docs/screenshots/simulation_demo.gif — used in the README and showcase.
"""

import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import simpledialog

from PIL import ImageGrab

from ftr.gui import DiagApp

OUT = Path("docs/screenshots/simulation_demo.gif")
FPS_INTERVAL = 0.34          # ~3 fps keeps the GIF small
SIZE = (810, 540)            # downscaled frame size

frames = []
recording = True
bbox = {"box": None}

# auto-answer any dialog the demo hits
simpledialog.askstring = lambda title, prompt, **kw: (
    "scratch between gears 1 2 3" if "Symptom" in title else
    "gears scratch between 1 and 2 — what is it, one sentence?")


def grabber():
    while recording:
        box = bbox["box"]
        if box is not None:
            try:
                frames.append(ImageGrab.grab(bbox=box).resize(SIZE))
            except Exception as e:
                print("grab error:", e)
        time.sleep(FPS_INTERVAL)


app = DiagApp(simulate=True)
app.geometry("900x600+60+60")
app.attributes("-topmost", True)
app.update()

current = {"win": app}
t = threading.Thread(target=grabber, daemon=True)
t.start()


def beat(seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.update()
        w = current["win"]
        try:
            bbox["box"] = (w.winfo_rootx(), w.winfo_rooty(),
                           w.winfo_rootx() + w.winfo_width(),
                           w.winfo_rooty() + w.winfo_height())
        except Exception:
            pass
        time.sleep(0.05)


beat(2)                       # opening shot
app.connect()
beat(2.5)                     # connect + mode badge
app.do_backup()
beat(2.5)
app.do_dtcs()
beat(4)                       # fault codes + part annotations scroll in
app.do_scan()
beat(5)                       # module scan
app.do_live()
beat(6)                       # live DPF numbers ticking
app.do_live()                 # stop

# component map: open, click the DPF sensor dot, show detail
app.do_map()
beat(1.5)
top = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)][0]
top.geometry("900x600+70+70")   # keep the window fully inside the capture
top.attributes("-topmost", True)
current["win"] = top
beat(1)
canvas = [w for w in top.winfo_children() if isinstance(w, tk.Canvas)][0]
dots = canvas.find_withtag("dot")
if dots:
    x0, y0, x1, y1 = canvas.coords(dots[0])
    canvas.event_generate("<Button-1>", x=int((x0 + x1) / 2),
                          y=int((y0 + y1) / 2))
beat(3.5)                     # part detail + clipboard line
top.destroy()
current["win"] = app
app.lift()
beat(1)

app.do_symptoms()             # monkeypatched dialog -> KB verdict
beat(4)
beat(2)                       # closing shot

recording = False
t.join(timeout=2)
app.destroy()

OUT.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:],
               duration=int(FPS_INTERVAL * 1000), loop=0, optimize=True)
print(f"saved {OUT} — {len(frames)} frames, "
      f"{OUT.stat().st_size // 1024} KB")
