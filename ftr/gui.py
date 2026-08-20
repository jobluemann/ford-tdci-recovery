"""Tkinter GUI for the suite — runs on Linux Mint and Windows, stdlib only.

Simulation mode (default) uses the scripted fake car: no adapter, no API
keys, no hardware — every button works against simulated data.
Real mode connects to an ELM327 on a serial port (USB or paired Bluetooth).

Linux Mint note: if tkinter is missing:  sudo apt install python3-tk
"""

import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, simpledialog

from . import known_issues, modules, obd
from .backup import take_snapshot
from .elm327 import ELM327, SimulatedECU
from .modules import SimulatedVehicle


class DiagApp(tk.Tk):
    def __init__(self, simulate=True):
        super().__init__()
        self.title("TDCi Recovery Diagnostics")
        self.geometry("860x560")
        self.q = queue.Queue()
        self.ecu = None
        self.vehicle = None
        self.live_running = False
        self.simulate = simulate

        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        self.sim_var = tk.BooleanVar(value=simulate)
        tk.Checkbutton(top, text="Simulation mode (fake car, no hardware)",
                       variable=self.sim_var).pack(side="left")
        tk.Label(top, text="Port:").pack(side="left", padx=(16, 2))
        self.port_entry = tk.Entry(top, width=14)
        self.port_entry.insert(0, "/dev/rfcomm0")
        self.port_entry.pack(side="left")
        tk.Button(top, text="Connect", command=self.connect).pack(side="left", padx=8)
        self.status = tk.Label(top, text="not connected", fg="#a33")
        self.status.pack(side="left", padx=8)

        btns = tk.Frame(self)
        btns.pack(fill="x", padx=8)
        for label, fn in [
            ("1. Backup snapshot", self.do_backup),
            ("2. Read fault codes", self.do_dtcs),
            ("3. Module scan", self.do_scan),
            ("4. Live DPF (start/stop)", self.do_live),
            ("5. Symptom lookup", self.do_symptoms),
            ("6. Post-battery checklist", self.do_checklist),
            ("7. Forum/RSS search", self.do_feeds),
            ("8. AI assistant", self.do_ai),
        ]:
            tk.Button(btns, text=label, command=fn).pack(side="left", padx=3)

        self.out = scrolledtext.ScrolledText(self, font=("Consolas", 10),
                                             state="disabled", wrap="word")
        self.out.pack(fill="both", expand=True, padx=8, pady=8)

        self.after(80, self._pump)

    # ---------- plumbing ----------
    def _pump(self):
        try:
            while True:
                line = self.q.get_nowait()
                self.out.configure(state="normal")
                self.out.insert("end", line + "\n")
                self.out.see("end")
                self.out.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(80, self._pump)

    def log(self, line):
        self.q.put(line)

    def _worker(self, fn):
        if not self.ecu:
            self.log("! Connect first (tick Simulation mode for the fake car).")
            return
        threading.Thread(target=fn, daemon=True).start()

    # ---------- connection ----------
    def connect(self):
        if self.sim_var.get():
            self.ecu, self.vehicle = SimulatedECU(), SimulatedVehicle()
            self.status.configure(text="connected: SIMULATED car", fg="#1e7b1e")
            self.log("=== Connected to the simulated vehicle ===")
        else:
            try:
                port = self.port_entry.get().strip() or None
                self.ecu = ELM327(port=port)
                self.vehicle = self.ecu
                self.status.configure(text=f"connected: {self.ecu.ser.port}", fg="#1e7b1e")
                self.log(f"=== Connected to ELM327 on {self.ecu.ser.port} ===")
            except Exception as e:
                self.status.configure(text="connection failed", fg="#a33")
                self.log(f"! Connection failed: {e}")

    # ---------- actions ----------
    def do_backup(self):
        def work():
            fname, snap = take_snapshot(self.ecu)
            self.log(f"Backup saved: {fname}")
            self.log(f"  VIN:  {snap['vehicle'].get('vin')}")
            self.log(f"  ECU:  {snap['vehicle'].get('ecu_name')}")
            self.log(f"  Cal:  {snap['vehicle'].get('calibration_id')}")
            self.log(f"  MIL:  {snap['status'].get('mil')}")
        self._worker(work)

    def do_dtcs(self):
        def work():
            codes = obd.decode_dtcs(self.ecu.query("03"))
            if not codes:
                self.log("No stored fault codes.")
                return
            self.log(f"{len(codes)} stored fault code(s):")
            for c in codes:
                note = obd.KNOWN_DTC.get(c, "")
                self.log(f"  {c}  {('- ' + note) if note else ''}")
        self._worker(work)

    def do_scan(self):
        def work():
            self.log("Scanning all modules…")
            modules.scan_modules(self.vehicle, log=self.log)
            self.log("Scan complete.")
        self._worker(work)

    def do_live(self):
        if self.live_running:
            self.live_running = False
            self.log("Live DPF stopped.")
            return
        self.live_running = True
        self.log("Live DPF pressure (sim: ~3.00 kPa). Press the button again to stop.")

        def work():
            while self.live_running:
                b = obd.data_bytes(self.ecu.query("22 F4 2B"), "F42B")
                if b and len(b) >= 2:
                    raw = (b[0] << 8) | b[1]
                    self.log(f"  {datetime.now():%H:%M:%S}  raw={raw} (~{raw/100.0:.2f} kPa - verify scaling)")
                else:
                    self.log(f"  {datetime.now():%H:%M:%S}  NO DATA")
                time.sleep(1.0)
        self._worker(work)

    def do_symptoms(self):
        text = simpledialog.askstring(
            "Symptom lookup",
            "Describe symptoms (e.g. 'scratch between gears 1 2 3'):",
            parent=self)
        if not text:
            return

        def work():
            kb = known_issues.load_kb()
            hits = known_issues.match(kb, symptom_text=text)
            if not hits:
                self.log("No KB match — try different wording.")
                return
            for score, issue, dh, sh in hits:
                for line in known_issues.render(score, issue, dh, sh).split("\n"):
                    self.log(line)
                self.log("")
        self._worker(work)

    def do_checklist(self):
        def work():
            from .cli import CHECKLIST_PATH
            try:
                for line in CHECKLIST_PATH.read_text(encoding="utf-8").split("\n"):
                    self.log(line)
            except FileNotFoundError:
                self.log("Checklist document not found.")
        self._worker(work)

    def do_feeds(self):
        kw = simpledialog.askstring(
            "Forum/RSS search",
            "Keywords (space separated, all must match):", parent=self)
        if not kw:
            return

        def work():
            import json as _json
            from . import feeds
            cfg = feeds.CACHE.parent.parent / "data" / "feeds.json"
            feed_list = feeds.DEFAULT_FEEDS
            if cfg.exists():
                feed_list = _json.loads(cfg.read_text(encoding="utf-8"))["feeds"]
            if not feed_list:
                self.log("No feeds configured. Add forum RSS URLs to data/feeds.json")
                return
            results, errors = feeds.search(feed_list, kw.split())
            for e in errors:
                self.log(f"(feed unavailable, used cache: {e})")
            self.log(f"{len(results)} result(s):")
            for it in results[:15]:
                self.log(f"  - {it['title']}")
                self.log(f"    {it['link']}")
        self._worker(work)

    def do_ai(self):
        q = simpledialog.askstring(
            "AI assistant",
            "Ask the diagnostic assistant (needs FTR_AI_PROVIDER + AI_API_KEY):",
            parent=self)
        if not q:
            return

        def work():
            from . import aichat
            try:
                reply, evidence = aichat.chat_grounded(q)
            except Exception as e:
                reply, evidence = f"(request failed: {e})", ""
            if evidence:
                self.log("--- auto-gathered evidence ---")
                for line in evidence.split("\n"):
                    self.log(line)
                self.log("------------------------------")
            self.log("ai> " + reply)
        self._worker(work)
