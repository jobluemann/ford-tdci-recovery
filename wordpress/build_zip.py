#!/usr/bin/env python3
"""Build dist/tdci-recovery-hub.zip — the uploadable WordPress plugin.

    python wordpress/build_zip.py

The zip has the plugin folder at its root (tdci-recovery-hub/…), exactly
what WordPress expects from Plugins → Add New → Upload Plugin.
"""

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "wordpress" / "tdci-recovery-hub"
OUT = ROOT / "dist" / "tdci-recovery-hub.zip"

OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(SRC.rglob("*")):
        if p.is_file():
            z.write(p, p.relative_to(SRC.parent))
print(f"built {OUT} ({OUT.stat().st_size} bytes)")
