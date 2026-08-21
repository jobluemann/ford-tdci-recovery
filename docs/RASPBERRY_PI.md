# Raspberry Pi model — the car stays plugged in

The suite is stdlib Python + tkinter, so it runs on any Raspberry Pi OS
(Lite or Desktop). Two sensible Pi models:

## Model A — Pi as the bridge (recommended, cheapest)

The Pi sits in the car (or garage) permanently connected to the OBD port.
Phones/tablets/laptops use the **PWA** over WiFi — no app installs.

**Hardware:** Pi Zero 2 W (~R350 / $15 class) + ELM327 USB cable
(or Bluetooth classic; the Pi's onboard BT works, `rfcomm` same as Mint).

```bash
# on the Pi (Raspberry Pi OS Lite is fine — no desktop needed)
sudo apt install python3-serial
git clone https://github.com/jobluemann/ford-tdci-recovery.git
cd ford-tdci-recovery

# USB adapter: nothing to set up, port appears as /dev/ttyUSB0
python3 ford_recovery.py --serve 8765 --port /dev/ttyUSB0

# Bluetooth classic adapter instead: bind once, then
sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF
python3 ford_recovery.py --serve 8765 --port /dev/rfcomm0
```

Then on any phone on the same WiFi: open the PWA (hosted on your site or
served from the Pi), enter the bridge URL `http://<pi-ip>:8765`, and read
codes / run the module scan from the phone.

**Auto-start on boot** (Pi as an appliance):

```
# /etc/systemd/system/tdci-bridge.service
[Unit]
Description=TDCi Recovery bridge
After=network.target

[Service]
WorkingDirectory=/home/pi/ford-tdci-recovery
ExecStart=/usr/bin/python3 ford_recovery.py --serve 8765 --port /dev/ttyUSB0
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

## Model B — Pi with a screen (full app)

Raspberry Pi OS **Desktop** + `sudo apt install python3-tk python3-serial`,
then `python3 gui_app.py --real` — the exact same GUI as the Mint laptop,
including the AI assistant (the Pi only needs internet for the AI; all
diagnostics are local).

## Power note

The OBD-II port supplies 12 V only for the adapter — the Pi needs its own
power (USB-C from the car or a small buck converter on a fused 12 V feed).
For a permanently-installed unit, use a supply with a low-voltage cutoff so
the Pi can't drain the battery — ironic on a project born from a battery
fault.
