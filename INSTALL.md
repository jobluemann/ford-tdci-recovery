# Installation Guide — TDCi Recovery Diagnostics

Pick your platform. **No admin rights needed on any of them.**

---

## 🪟 Windows — easiest: the portable build (recommended)

1. Download **[tdci-recovery-windows-portable.zip](https://github.com/jobluemann/ford-tdci-recovery/releases/download/v0.5.0/tdci-recovery-windows-portable.zip)**
2. Unzip anywhere — Desktop, Documents, a USB stick. No installer runs.
3. Double-click **`tdci-recovery.exe`**.
   - If Windows SmartScreen asks: *More info → Run anyway* (the exe is unsigned — normal for open source).
4. The app opens in **SIMULATION mode** — a fake car so you can click every
   button safely. Nothing you do in simulation touches a real vehicle.

That's it. No Python, no admin, no drivers to install for the app itself.

---

## 🐧 Linux Mint — option A: the .deb package

```bash
git clone https://github.com/jobluemann/ford-tdci-recovery.git
cd ford-tdci-recovery
sudo apt install ./dist/tdci-recovery_0.4.0_all.deb
```

Then find **TDCi Recovery** in your applications menu (or run `tdci-recovery`).

> If `apt`/`dpkg` throws an error on your machine, the GUI "Software"
> manager can install the .deb by double-click — or use option B below,
> which needs no package manager at all.

## 🐧 Linux Mint — option B: run from the folder

```bash
sudo apt install python3-tk git      # one time
git clone https://github.com/jobluemann/ford-tdci-recovery.git
cd ford-tdci-recovery
python3 gui_app.py
```

Optional menu/panel shortcut:

```bash
bash scripts/install_desktop_shortcut.sh
```

---

## 🔌 Connecting a real vehicle

You need an **ELM327 adapter** (USB cable or Bluetooth). See
`docs/ADAPTERS.md` for buying advice.

### USB cable
- **Windows:** plug in → check Device Manager for the COM port (e.g. `COM5`).
- **Linux:** plug in → port appears as `/dev/ttyUSB0`.

### Bluetooth adapter
- **Windows:** Settings → Bluetooth → pair the adapter (PIN usually `1234`
  or `0000`) → *More Bluetooth options → COM ports* → note the **outgoing**
  port (e.g. `COM6`).
- **Linux Mint:** pair in the Bluetooth manager, then:
  ```bash
  rfcomm bind 0 <adapter-MAC>     # creates /dev/rfcomm0
  ```
  Full walkthrough: `docs/BLUETOOTH_SETUP.md`.

### In the app
1. **Untick** SIMULATION.
2. Press **Detect** — the app lists real ports and fills the first one in
   (or type the port yourself).
3. Press **CONNECT**. The header badge turns green: **● LIVE VEHICLE**.
4. Run **1 · BACKUP** before anything else. Always.

---

## 🤖 AI assistant + voice (optional, free)

1. In the app press **AI SETUP**.
2. Get a free key at <https://console.groq.com> (sign in → API Keys →
   Create — no credit card).
3. Paste it, press **Save + Test** → "✓ works".
4. Pick a **voice** while you're there (default: autumn).
5. Tick **VOICE** in the main window if you want the plain-English part of
   every AI answer read aloud.

Everything except button 8 works without any key, fully offline.

---

## 🗂️ Where your data lives

| What | Git-clone run | .deb install | Windows portable |
|---|---|---|---|
| Backups | `backups/` in the folder | `~/.local/share/tdci-recovery/backups/` | your user profile |
| AI key (saved locally) | `data/ai_config.json` | `~/.local/share/tdci-recovery/` | your user profile |

Your AI key never leaves your machine except directly to the AI provider
you chose. VINs are stripped from anything shared.

---

## 🆘 Troubleshooting

| Symptom | Fix |
|---|---|
| `python3-tk` missing on Mint | `sudo apt install python3-tk` |
| "No serial ports found" | Adapter not paired/plugged — see Bluetooth/USB steps above |
| Connect fails on Bluetooth | Pair again; confirm the **outgoing** COM port, not incoming |
| Windows says app is unrecognized | SmartScreen → *More info → Run anyway* |
| Voice silent on Linux | `sudo apt install pulseaudio-utils` (paplay) or `alsa-utils` (aplay) |
| Want to start over | Delete `data/ai_config.json` (git-clone) or `~/.local/share/tdci-recovery/` (.deb) |
