"""Capture a real screenshot of the component map window."""
import time
import tkinter as tk
from pathlib import Path

from PIL import ImageGrab

from ftr.gui import DiagApp

app = DiagApp(simulate=True)
app.geometry("900x600+40+40")
app.attributes("-topmost", True)  # stay above other windows for the capture
app.update()

app.do_map()
app.update()
top = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)][0]
top.attributes("-topmost", True)
time.sleep(0.6)
app.update()  # let the deferred draw() run

top.lift()
top.focus_force()
app.update()
time.sleep(0.8)

# engine-bay view
x = top.winfo_rootx(); y = top.winfo_rooty()
img = ImageGrab.grab(bbox=(x, y, x + top.winfo_width(), y + top.winfo_height()))
out = Path("docs/screenshots")
out.mkdir(parents=True, exist_ok=True)
img.save(out / "component_map_engine_bay.png")

# click the DPF pressure sensor dot programmatically: show its detail
from ftr import parts
comp = [c for c in parts.load() if c["id"] == "dpf_pressure_sensor"][0]
# simulate the click handler by invoking show via the canvas binding:
canvas = [w for w in top.winfo_children() if isinstance(w, tk.Canvas)][0]
# find the dot nearest the component's mapped position and trigger binding
w = canvas.winfo_width(); h = 330
cx = 20 + (w - 40) * comp["map"]["x"] / 100.0
cy = 30 + (h - 50) * comp["map"]["y"] / 100.0
item = canvas.find_closest(cx, cy)
canvas.event_generate("<Button-1>", x=int(cx), y=int(cy))
app.update()
time.sleep(0.5)

x = top.winfo_rootx(); y = top.winfo_rooty()
img2 = ImageGrab.grab(bbox=(x, y, x + top.winfo_width(), y + top.winfo_height()))
img2.save(out / "component_map_dpf_sensor_selected.png")

# underside view
for w2 in top.winfo_children():
    if isinstance(w2, tk.Frame):
        for rb in w2.winfo_children():
            if isinstance(rb, tk.Radiobutton) and rb.cget("value") == "underside":
                rb.invoke()
app.update()
time.sleep(0.5)
x = top.winfo_rootx(); y = top.winfo_rooty()
img3 = ImageGrab.grab(bbox=(x, y, x + top.winfo_width(), y + top.winfo_height()))
img3.save(out / "component_map_underside.png")

# main window with a DTC readout showing part annotation
top.destroy()  # close the map so the main window is unobstructed
app.deiconify()
app.attributes("-topmost", True)
app.lift()
app.focus_force()
app.connect()
app.do_dtcs()
t0 = time.time()
while time.time() - t0 < 4:
    app.update()
    time.sleep(0.05)
app.lift()
app.update()
time.sleep(0.5)
x = app.winfo_rootx(); y = app.winfo_rooty()
img4 = ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height()))
img4.save(out / "main_window_dtc_parts.png")

app.destroy()
print("saved 4 screenshots to docs/screenshots/")
