#!/usr/bin/env python3
"""Build the portable no-admin Windows package.

  python -m venv .build-venv
  .build-venv\\Scripts\\pip install pyinstaller
  python tools\\build_windows.py

Output: dist/tdci-recovery.exe  +  dist/tdci-recovery-windows-portable.zip
The exe is one-file, windowed (no console), needs no install/admin.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VENV_PYI = ROOT / ".build-venv" / "Scripts" / "pyinstaller.exe"


def main():
    pyi = VENV_PYI if VENV_PYI.exists() else "pyinstaller"
    subprocess.check_call([
        str(pyi), "--onefile", "--windowed", "--name", "tdci-recovery",
        "--add-data", "data;data", "--add-data", "docs;docs",
        "--clean", "gui_app.py",
    ], cwd=ROOT)

    pkg = DIST / "tdci-recovery-windows"
    pkg.mkdir(exist_ok=True)
    shutil.copy(DIST / "tdci-recovery.exe", pkg)
    shutil.copy(DIST / "PORTABLE-README.txt", pkg)
    shutil.make_archive(str(DIST / "tdci-recovery-windows-portable"),
                        "zip", root_dir=DIST, base_dir="tdci-recovery-windows")
    shutil.rmtree(pkg)
    print("Built:", DIST / "tdci-recovery-windows-portable.zip")


if __name__ == "__main__":
    sys.exit(main())
