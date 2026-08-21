#!/bin/bash
# install_desktop_shortcut.sh — add "TDCi Recovery" to the Mint app menu.
#
#   bash scripts/install_desktop_shortcut.sh
#
# Creates ~/.local/share/applications/tdci-recovery.desktop pointing at
# gui_app.py in this repo. After this, the app is in the Mint menu and can
# be pinned to the panel — no terminal needed to launch it.

set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APPS="$HOME/.local/share/applications"
mkdir -p "$APPS"

cat > "$APPS/tdci-recovery.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TDCi Recovery Diagnostics
Comment=Ford 2.0 TDCi open-source diagnostics
Exec=python3 $REPO/gui_app.py
Path=$REPO
Icon=$REPO/site/pwa/icon.svg
Terminal=false
Categories=Utility;
EOF

chmod +x "$APPS/tdci-recovery.desktop"
if command -v update-desktop-database >/dev/null; then
    update-desktop-database "$APPS" 2>/dev/null || true
fi

echo "Installed. Find 'TDCi Recovery Diagnostics' in the Mint menu (Utility),"
echo "right-click it to pin to the panel. First launch opens in simulation"
echo "mode — untick 'Simulation mode' for the real car."
