#!/bin/bash
# mint_bluetooth_setup.sh — pair + bind a classic Bluetooth ELM327 on Linux Mint.
#
#   bash scripts/mint_bluetooth_setup.sh
#
# Classic Bluetooth ELM327 adapters speak SPP (serial). Linux exposes that as
# /dev/rfcomm0 after a bind. This script does the one-time setup and checks.
# After it: untick "Simulation mode" in the app, port /dev/rfcomm0, Connect.

set -e

echo "=== TDCi Recovery — Mint Bluetooth ELM327 setup ==="

# 1. bluez installed?
if ! command -v bluetoothctl >/dev/null; then
    echo "Installing Bluetooth tools (sudo)…"
    sudo apt-get update && sudo apt-get install -y bluez rfcomm
fi

# 2. adapter MAC
if [ -z "$1" ]; then
    echo ""
    echo "Put the ELM327 in the car (ignition ON), then scan:"
    echo "  bluetoothctl scan on     # look for OBDII / ELM327 / V-LINK etc."
    echo ""
    read -rp "Adapter MAC address (AA:BB:CC:DD:EE:FF): " MAC
else
    MAC="$1"
fi

# 3. pair + trust (PIN is usually 1234 or 0000)
echo "Pairing $MAC (PIN is usually 1234 or 0000)…"
bluetoothctl pair "$MAC" || true
bluetoothctl trust "$MAC"

# 4. serial-port permission without sudo (dialout group)
if ! groups "$USER" | grep -q dialout; then
    echo "Adding $USER to the dialout group (serial access, no sudo)…"
    sudo usermod -aG dialout "$USER"
    echo "! Log out and back in once for this to take effect."
fi

# 5. bind the serial port
echo "Binding /dev/rfcomm0…"
sudo rfcomm release 0 2>/dev/null || true
sudo rfcomm bind 0 "$MAC"

# 6. auto-bind on boot (optional but recommended for a dedicated laptop)
if ! grep -q rfcomm /etc/rc.local 2>/dev/null; then
    echo ""
    echo "Optional: auto-bind on boot. Add this line to /etc/rc.local"
    echo "(before 'exit 0'), or create a systemd unit:"
    echo "    rfcomm bind 0 $MAC &"
fi

# 7. verify
echo ""
if [ -e /dev/rfcomm0 ]; then
    echo "OK: /dev/rfcomm0 exists."
    echo "Test the link:  python3 ford_recovery.py --port /dev/rfcomm0"
    echo "Or the GUI:     python3 gui_app.py --real  (port: /dev/rfcomm0)"
else
    echo "Bind failed. Check the adapter is powered and paired (bluetoothctl devices)."
fi
