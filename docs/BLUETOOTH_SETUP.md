# Bluetooth ELM327 setup

The app talks to any ELM327 that presents a **serial port**. Classic
Bluetooth adapters (the common ~R200–R400 / $10–$25 "OBDII Bluetooth" dongles)
use SPP serial — that works. BLE-only adapters need the PWA's Web Bluetooth
path instead (see `site/pwa/`).

## Linux Mint (the recommended setup)

One-time, with the adapter plugged into the car and ignition ON:

```bash
bash scripts/mint_bluetooth_setup.sh          # interactive, does everything
# or by hand:
bluetoothctl scan on                          # find the adapter MAC
bluetoothctl pair AA:BB:CC:DD:EE:FF           # PIN usually 1234 or 0000
bluetoothctl trust AA:BB:CC:DD:EE:FF
sudo usermod -aG dialout $USER                # serial access without sudo (log out/in once)
sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF          # creates /dev/rfcomm0
```

Then:

```bash
python3 gui_app.py --real        # port: /dev/rfcomm0
# or CLI:
python3 ford_recovery.py --port /dev/rfcomm0
```

To auto-bind on boot (dedicated diagnostics laptop), add
`rfcomm bind 0 AA:BB:CC:DD:EE:FF &` to `/etc/rc.local` or a systemd unit.

## Windows

1. Pair the adapter (Settings → Bluetooth → Add device; PIN 1234/0000).
2. Open *Bluetooth settings → More Bluetooth options → COM ports* and note
   the **outgoing** COM port.
3. `python gui_app.py --real`, enter that COM port.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `No serial ports found` | not bound / not paired | rerun the setup script |
| bind works, connect times out | ignition off / adapter asleep | key ON, re-plug adapter |
| garbled responses | cheap clone with wrong baud | try baud 9600–115200 (`ELM327(port, baud=…)`) |
| DEM/AWD module shows `BUS?` | adapter is HS-CAN only | need an adapter with an **HS/MS-CAN switch** — see `docs/ADAPTERS.md` |
| permission denied on /dev/rfcomm0 | not in dialout group | `sudo usermod -aG dialout $USER`, log out/in |
