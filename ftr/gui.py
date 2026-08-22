"""Tkinter GUI for the suite — runs on Linux Mint and Windows.

Simulation mode (default) uses the scripted fake car: no adapter, no API
keys, no hardware — every button works against simulated data.
Real mode connects to an ELM327 on a serial port (USB or paired Bluetooth).

Dark "digital dashboard" theme, stdlib tkinter only.
Linux Mint note: if tkinter is missing:  sudo apt install python3-tk
"""

import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, simpledialog, ttk

from . import aiconfig, known_issues, modules, obd, parts
from .backup import take_snapshot
from .elm327 import ELM327, SimulatedECU
from .modules import SimulatedVehicle

# ---- digital dashboard palette ----
BG = "#0b0f14"        # near-black blue
PANEL = "#12181f"     # raised panel
BORDER = "#1f6f5c"    # dim teal border
FG = "#d5e2ea"        # primary text
DIM = "#7d8a96"       # secondary text
ACCENT = "#19e3b1"    # neon mint — headers, highlights
LIVE = "#21d07a"      # live/connected green
SIM = "#f0a832"       # simulation amber
ERR = "#ff5470"       # error red-pink
PART = "#4cc2ff"      # part-info cyan
FONT_UI = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 10)


class DiagApp(tk.Tk):
    def __init__(self, simulate=True):
        super().__init__()
        self.title("TDCi Recovery — Digital Diagnostics")
        self.geometry("980x620")
        self.configure(bg=BG)
        self.q = queue.Queue()
        self.ecu = None
        self.vehicle = None
        self.ai_history = []  # AI chat memory for this session
        self.live_running = False
        self.simulate = simulate
        self._style_ttk()

        # ---------- header ----------
        header = tk.Frame(self, bg=PANEL, highlightbackground=BORDER,
                          highlightthickness=1)
        header.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(header, text="◤ TDCI RECOVERY", bg=PANEL, fg=ACCENT,
                 font=(FONT_UI[0], 14, "bold")).pack(side="left", padx=10, pady=6)
        self.mode_badge = tk.Label(header, text=" OFFLINE ", bg=PANEL,
                                   fg=DIM, font=(FONT_UI[0], 10, "bold"))
        self.mode_badge.pack(side="right", padx=10)

        # ---------- connection bar ----------
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=10, pady=4)
        self.sim_var = tk.BooleanVar(value=simulate)
        tk.Checkbutton(top, text="SIMULATION (fake car, no hardware)",
                       variable=self.sim_var, bg=BG, fg=SIM,
                       selectcolor=PANEL, activebackground=BG,
                       activeforeground=SIM,
                       font=FONT_UI).pack(side="left")
        tk.Label(top, text="Port:", bg=BG, fg=DIM,
                 font=FONT_UI).pack(side="left", padx=(16, 2))
        self.port_entry = tk.Entry(top, width=14, bg=PANEL, fg=FG,
                                   insertbackground=ACCENT, relief="flat")
        self.port_entry.insert(0, "COM5" if os.name == "nt" else "/dev/rfcomm0")
        self.port_entry.pack(side="left", ipady=2)
        tk.Button(top, text="Detect", command=self.detect_ports,
                  bg=PANEL, fg=DIM, activebackground=BORDER, relief="flat",
                  font=FONT_UI).pack(side="left", padx=4)
        self.voice_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text="VOICE", variable=self.voice_var,
                       bg=BG, fg=PART, selectcolor=PANEL,
                       activebackground=BG, activeforeground=PART,
                       font=(FONT_UI[0], 10, "bold")).pack(side="left",
                                                           padx=(12, 0))
        tk.Button(top, text="CONNECT", command=self.connect,
                  bg=BORDER, fg="#ffffff", activebackground=ACCENT,
                  activeforeground=BG, relief="flat",
                  font=(FONT_UI[0], 10, "bold")).pack(side="left", padx=8)
        self.status = tk.Label(top, text="not connected", bg=BG, fg=ERR,
                               font=FONT_UI)
        self.status.pack(side="left", padx=8)

        # ---------- action buttons (two rows) ----------
        rows = [
            [("1 · BACKUP", self.do_backup),
             ("2 · FAULT CODES", self.do_dtcs),
             ("3 · MODULE SCAN", self.do_scan),
             ("4 · LIVE DPF", self.do_live),
             ("5 · SYMPTOMS", self.do_symptoms)],
            [("6 · BATTERY RESET", self.do_checklist),
             ("7 · FORUMS", self.do_feeds),
             ("8 · AI ASSISTANT", self.do_ai),
             ("9 · COMPONENT MAP", self.do_map),
             ("AI SETUP", self.do_ai_setup)],
        ]
        for row in rows:
            btns = tk.Frame(self, bg=BG)
            btns.pack(fill="x", padx=10, pady=(2, 0))
            for label, fn in row:
                tk.Button(btns, text=label, command=fn, bg=PANEL, fg=FG,
                          activebackground=BORDER, activeforeground="#ffffff",
                          relief="flat", font=(FONT_UI[0], 9, "bold"),
                          padx=8).pack(side="left", padx=3, pady=2,
                                       fill="x", expand=True)

        # ---------- output console ----------
        frame = tk.Frame(self, bg=BORDER)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.out = scrolledtext.ScrolledText(
            frame, font=FONT_MONO, state="disabled", wrap="word",
            bg=BG, fg=FG, insertbackground=ACCENT, relief="flat",
            selectbackground=BORDER)
        self.out.pack(fill="both", expand=True, padx=1, pady=1)
        # colour-coded line types
        self.out.tag_configure("hdr", foreground=ACCENT)
        self.out.tag_configure("err", foreground=ERR)
        self.out.tag_configure("ai", foreground=PART)
        self.out.tag_configure("part", foreground=LIVE)
        self.out.tag_configure("dim", foreground=DIM)

        aiconfig.apply()  # load saved AI settings (env vars still win)
        self.log("TDCi Recovery ready — simulation is ON, every button is "
                 "safe to try.", "hdr")
        self.after(80, self._pump)

    def _style_ttk(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=PANEL, background=PANEL,
                        foreground=FG)

    # ---------- plumbing ----------
    def _pump(self):
        try:
            while True:
                line, tag = self.q.get_nowait()
                self.out.configure(state="normal")
                self.out.insert("end", line + "\n", tag)
                self.out.see("end")
                self.out.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(80, self._pump)

    def log(self, line, tag=None):
        if tag is None:
            if line.startswith("!") or "failed" in line.lower():
                tag = "err"
            elif line.startswith("===") or line.startswith("TDCi"):
                tag = "hdr"
            elif line.startswith("ai>"):
                tag = "ai"
            elif "→ part:" in line or "copied to clipboard" in line:
                tag = "part"
        self.q.put((line, tag))

    def _worker(self, fn):
        if not self.ecu:
            self.log("! Connect first (SIMULATION ticked = fake car).", "err")
            return
        threading.Thread(target=fn, daemon=True).start()

    # ---------- connection ----------
    def detect_ports(self):
        """List real serial ports into the log (needs pyserial)."""
        try:
            from serial.tools import list_ports
            found = [f"{p.device} — {p.description}"
                     for p in list_ports.comports()]
        except ImportError:
            self.log("! pyserial not available — type the port manually "
                     "(COM5 on Windows, /dev/rfcomm0 on Linux).", "err")
            return
        if not found:
            self.log("No serial ports found. Plug in / pair the adapter first.")
            return
        self.log("Serial ports detected:")
        for f in found:
            self.log(f"  {f}")
        # auto-fill the first port for convenience
        self.port_entry.delete(0, "end")
        self.port_entry.insert(0, found[0].split(" — ")[0])

    def connect(self):
        # switching modes or reconnecting: drop the old session cleanly
        if self.ecu is not None:
            try:
                self.ecu.close()
            except Exception:
                pass
            self.ecu = self.vehicle = None
        if self.sim_var.get():
            self.ecu, self.vehicle = SimulatedECU(), SimulatedVehicle()
            self.status.configure(text="connected: SIMULATED car", fg=SIM)
            self.mode_badge.configure(text=" ● SIMULATION ", fg=SIM)
            self.log("=== Connected to the simulated vehicle ===")
        else:
            port = self.port_entry.get().strip() or None
            if not port:
                self.log("! Enter the adapter port first (or press Detect).",
                         "err")
                self.status.configure(text="no port given", fg=ERR)
                return
            try:
                self.ecu = ELM327(port=port)
                self.vehicle = self.ecu
                self.status.configure(
                    text=f"connected: {self.ecu.ser.port}", fg=LIVE)
                self.mode_badge.configure(text=" ● LIVE VEHICLE ", fg=LIVE)
                self.log(f"=== Connected to ELM327 on {self.ecu.ser.port} ===")
                self.log("! LIVE mode: this is a real vehicle. Always run "
                         "'1 · BACKUP' before clearing anything.", "err")
            except BaseException as e:  # SystemExit from missing pyserial too
                self.status.configure(text="connection failed", fg=ERR)
                self.mode_badge.configure(text=" OFFLINE ", fg=DIM)
                self.log(f"! Connection failed: {e}", "err")

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
                comps = parts.for_code(c)
                for comp in comps:
                    self.log(f"      → part: {comp['name']}"
                             + (f"  ({', '.join(comp['part_numbers'])})"
                                if comp.get("part_numbers") else ""))
                    self.log(f"        {comp['location']}", "dim")
            if any(parts.for_code(c) for c in codes):
                self.log("  (open '9 · COMPONENT MAP' to see where these "
                         "parts sit)", "dim")
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
        self.log("Live DPF pressure (sim: ~3.00 kPa). Press the button again "
                 "to stop.", "hdr")

        def work():
            while self.live_running:
                b = obd.data_bytes(self.ecu.query("22 F4 2B"), "F42B")
                if b and len(b) >= 2:
                    raw = (b[0] << 8) | b[1]
                    self.log(f"  {datetime.now():%H:%M:%S}  raw={raw} "
                             f"(~{raw/100.0:.2f} kPa - verify scaling)")
                else:
                    self.log(f"  {datetime.now():%H:%M:%S}  NO DATA", "err")
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
                self.log("Checklist document not found.", "err")
        self._worker(work)

    def do_feeds(self):
        kw = simpledialog.askstring(
            "Forum/RSS search",
            "Keywords (space separated, all must match):", parent=self)
        if not kw:
            return

        def work():
            import json as _json
            from . import feeds, paths
            cfg = paths.REPO_ROOT / "data" / "feeds.json"
            feed_list = feeds.DEFAULT_FEEDS
            if cfg.exists():
                feed_list = _json.loads(cfg.read_text(encoding="utf-8"))["feeds"]
            if not feed_list:
                self.log("No feeds configured. Add forum RSS URLs to "
                         "data/feeds.json")
                return
            results, errors = feeds.search(feed_list, kw.split())
            for e in errors:
                self.log(f"(feed unavailable, used cache: {e})", "dim")
            self.log(f"{len(results)} result(s):")
            for it in results[:15]:
                self.log(f"  - {it['title']}")
                self.log(f"    {it['link']}", "dim")
        self._worker(work)

    # ---------- component map ----------
    def do_map(self):
        comps = parts.load()
        if not comps:
            self.log("data/parts.json missing or empty.", "err")
            return
        win = tk.Toplevel(self)
        win.title("Component map — Kuga 2.0 TDCi (click a dot)")
        win.geometry("900x600")
        win.configure(bg=BG)

        view = tk.StringVar(value="engine_bay")
        bar = tk.Frame(win, bg=PANEL, highlightbackground=BORDER,
                       highlightthickness=1)
        bar.pack(fill="x", padx=8, pady=4)
        for text, val in (("Engine bay", "engine_bay"),
                          ("Underside", "underside")):
            tk.Radiobutton(bar, text=text, variable=view, value=val,
                           command=lambda: draw(), bg=PANEL, fg=FG,
                           selectcolor=BG, activebackground=PANEL,
                           activeforeground=ACCENT,
                           font=FONT_UI).pack(side="left", padx=6, pady=4)
        tk.Label(bar, text="Verify part numbers against your VIN (Ford ETIS).",
                 bg=PANEL, fg=SIM, font=FONT_UI).pack(side="right", padx=8)

        canvas = tk.Canvas(win, bg=BG, highlightthickness=0, height=360)
        canvas.pack(fill="both", expand=True, padx=8)
        detail = tk.Text(win, height=10, font=FONT_MONO, wrap="word",
                         bg=PANEL, fg=FG, insertbackground=ACCENT,
                         relief="flat")
        detail.pack(fill="x", padx=8, pady=6)
        detail.insert("end", "Click a component dot to see location, "
                             "Ford part numbers and what this app can test.")
        detail.configure(state="disabled")

        def show(comp):
            detail.configure(state="normal")
            detail.delete("1.0", "end")
            detail.insert("end", parts.describe(comp))
            detail.configure(state="disabled")
            self.clipboard_clear()
            if comp.get("part_numbers"):
                self.clipboard_append(comp["part_numbers"][0])
                self.log(f"Component map: {comp['name']} — first part number "
                         f"copied to clipboard ({comp['part_numbers'][0]})")

        def draw():
            canvas.delete("all")
            w = max(canvas.winfo_width(), 720)
            h = 350
            canvas.create_rectangle(20, 34, w - 20, h - 20, outline=BORDER,
                                    width=2)
            canvas.create_text(30, 18, anchor="w", fill=DIM, font=FONT_UI,
                               text=("FRONT → engine bay (bonnet open, top view)"
                                     if view.get() == "engine_bay"
                                     else "FRONT → underside view (car lifted)"))
            for comp in comps:
                m = comp.get("map", {})
                if m.get("view") != view.get():
                    continue
                x = 20 + (w - 40) * m.get("x", 50) / 100.0
                y = 34 + (h - 54) * m.get("y", 50) / 100.0
                r = 10
                dot = canvas.create_oval(x - r, y - r, x + r, y + r,
                                         fill=ERR, outline=ACCENT,
                                         width=2, tags=("dot",))
                canvas.create_text(x, y - r - 10, fill=FG,
                                   font=(FONT_UI[0], 8, "bold"),
                                   text=comp["name"].split("(")[0].strip())
                canvas.tag_bind(dot, "<Button-1>",
                                lambda e, c=comp: show(c))

        win.after(50, draw)
        win.bind("<Configure>", lambda e: draw() if e.widget is win else None)

    # ---------- AI setup (no environment variables needed) ----------
    def do_ai_setup(self):
        cfg = aiconfig.load()
        win = tk.Toplevel(self)
        win.title("AI Setup — paste your key, press Save")
        win.geometry("580x375")
        win.configure(bg=BG)
        win.transient(self)

        tk.Label(win, text="1. Get a FREE key at https://console.groq.com "
                 "(sign in → API Keys → Create). No credit card.",
                 wraplength=550, justify="left", bg=BG, fg=FG,
                 font=FONT_UI).pack(anchor="w", padx=12, pady=(10, 4))

        frm = tk.Frame(win, bg=BG)
        frm.pack(fill="x", padx=12, pady=4)

        tk.Label(frm, text="2. Provider:", bg=BG, fg=DIM,
                 font=FONT_UI).grid(row=0, column=0, sticky="w")
        provider = ttk.Combobox(frm, state="readonly", width=14,
                                values=["groq", "openrouter", "gemini",
                                        "grok", "ollama", "custom"])
        provider.set(cfg.get("FTR_AI_PROVIDER", "groq"))
        provider.grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(frm, text="3. API key:", bg=BG, fg=DIM,
                 font=FONT_UI).grid(row=1, column=0, sticky="w", pady=6)
        key_entry = tk.Entry(frm, width=44, show="•", bg=PANEL, fg=FG,
                             insertbackground=ACCENT, relief="flat")
        key_entry.insert(0, cfg.get("GROQ_API_KEY") or cfg.get("AI_API_KEY", ""))
        key_entry.grid(row=1, column=1, columnspan=2, sticky="w", padx=6)
        show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frm, text="show", variable=show_var, bg=BG, fg=DIM,
                       selectcolor=PANEL, activebackground=BG,
                       command=lambda: key_entry.configure(
                           show="" if show_var.get() else "•")
                       ).grid(row=1, column=3)

        tk.Label(frm, text="Fast model:", bg=BG, fg=DIM,
                 font=FONT_UI).grid(row=2, column=0, sticky="w")
        research = tk.Entry(frm, width=44, bg=PANEL, fg=FG,
                            insertbackground=ACCENT, relief="flat")
        research.insert(0, cfg.get("FTR_RESEARCH_MODEL",
                                   aiconfig.DEFAULT_RESEARCH_MODEL))
        research.grid(row=2, column=1, columnspan=2, sticky="w", padx=6)

        tk.Label(frm, text="Smart model:", bg=BG, fg=DIM,
                 font=FONT_UI).grid(row=3, column=0, sticky="w", pady=6)
        diag = tk.Entry(frm, width=44, bg=PANEL, fg=FG,
                        insertbackground=ACCENT, relief="flat")
        diag.insert(0, cfg.get("FTR_DIAG_MODEL", aiconfig.DEFAULT_DIAG_MODEL))
        diag.grid(row=3, column=1, columnspan=2, sticky="w", padx=6)

        tk.Label(frm, text="Voice:", bg=BG, fg=DIM,
                 font=FONT_UI).grid(row=4, column=0, sticky="w")
        voice = ttk.Combobox(frm, state="readonly", width=14,
                             values=["autumn", "diana", "hannah",
                                     "austin", "daniel", "troy"])
        voice.set(cfg.get("FTR_TTS_VOICE", "autumn"))
        voice.grid(row=4, column=1, sticky="w", padx=6)
        tk.Label(frm, text="(reads the plain-English answer aloud when "
                 "VOICE is ticked)", bg=BG, fg=DIM,
                 font=(FONT_UI[0], 8)).grid(row=4, column=2, sticky="w")

        tk.Label(win, text="Leave the model names as-is unless you know what "
                 "you're doing — the defaults are free and current.",
                 fg=DIM, bg=BG, wraplength=550, justify="left",
                 font=FONT_UI).pack(anchor="w", padx=12)

        status = tk.Label(win, text="", fg=LIVE, bg=BG, font=FONT_UI)
        status.pack(anchor="w", padx=12, pady=(4, 0))

        def save_and_apply():
            prov = provider.get()
            key = key_entry.get().strip()
            cfg = {"FTR_AI_PROVIDER": prov,
                   "FTR_RESEARCH_PROVIDER": prov,
                   "FTR_DIAG_PROVIDER": prov,
                   "FTR_RESEARCH_MODEL": research.get().strip(),
                   "FTR_DIAG_MODEL": diag.get().strip(),
                   "FTR_TTS_VOICE": voice.get().strip() or "autumn"}
            if key:
                cfg["AI_API_KEY"] = key
                if prov == "groq":
                    cfg["GROQ_API_KEY"] = key
            aiconfig.save(cfg)
            aiconfig.apply(cfg, force=True)  # overwrite any key already in memory
            self.log("AI setup saved. The AI assistant button is ready to use.")

        def test():
            save_and_apply()
            status.configure(text="testing…", fg=DIM)
            win.update_idletasks()

            def work():
                from . import aichat
                try:
                    reply = aichat.chat(
                        [{"role": "user", "content":
                          "Reply with exactly: AI connection OK"}])
                    ok = "AI connection OK" in reply
                    text = ("✓ works — the AI answered" if ok
                            else f"answered: {reply[:80]}")
                    colour = LIVE if ok else ERR
                except Exception as e:
                    text, colour = f"✗ failed: {e}", ERR
                win.after(0, lambda: status.configure(text=text, fg=colour))
            threading.Thread(target=work, daemon=True).start()

        row = tk.Frame(win, bg=BG)
        row.pack(anchor="w", padx=12, pady=10)
        for label, fn in (("Save", save_and_apply), ("Save + Test", test),
                          ("Close", win.destroy)):
            tk.Button(row, text=label, command=fn, bg=PANEL, fg=FG,
                      activebackground=BORDER, relief="flat",
                      font=FONT_UI).pack(side="left", padx=4)

    def do_ai(self):
        if not aiconfig.configured():
            if messagebox.askyesno(
                    "AI not set up yet",
                    "The AI assistant needs a free API key (2 minutes, "
                    "no credit card).\n\nOpen the AI Setup window now?",
                    parent=self):
                self.do_ai_setup()
            return
        q = simpledialog.askstring(
            "AI assistant",
            "Ask the diagnostic assistant:",
            parent=self)
        if not q:
            return

        def work():
            from . import aichat
            try:
                reply, evidence = aichat.chat_grounded(
                    q, history=list(self.ai_history))
            except Exception as e:
                reply, evidence = f"(request failed: {e})", ""
            # remember the exchange so follow-up questions keep context;
            # cap at the last 10 exchanges to control the token budget
            self.ai_history = (self.ai_history
                               + [{"role": "user", "content": q},
                                  {"role": "assistant", "content": reply}])[-20:]
            if evidence:
                self.log("--- auto-gathered evidence ---", "dim")
                for line in evidence.split("\n"):
                    self.log(line, "dim")
                self.log("------------------------------", "dim")
            self.log("ai> " + reply)
            if self.voice_var.get() and not reply.startswith("(request failed"):
                try:
                    from . import tts
                    spoken = tts.plain_english_section(reply)
                    self.log("voice> " + spoken[:120] + "…", "ai")
                    tts.speak(spoken,
                              voice=os.environ.get("FTR_TTS_VOICE", "autumn"))
                except Exception as e:
                    self.log(f"! voice failed: {e}", "err")
        self._worker(work)
