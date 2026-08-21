#!/usr/bin/env python3
"""Build dist/tdci-recovery_<ver>_all.deb — pure stdlib, no dpkg needed.

A .deb is an `ar` archive holding debian-binary, control.tar.gz and
data.tar.gz. This script writes all three directly, so the package can be
built on Windows or Linux without any Debian tooling:

    python packaging/build_deb.py

Install on Mint/Debian/Ubuntu:
    sudo apt install ./dist/tdci-recovery_0.4.0_all.deb
(apt resolves the python3-tk / python3-serial dependencies automatically;
on a broken dpkg, run `sudo dpkg --configure -a` first.)

Layout installed:
    /usr/share/tdci-recovery/     the app (read-only)
    /usr/local/bin/tdci-recovery  launcher (opens the GUI)
    /usr/share/applications/tdci-recovery.desktop   menu entry
    /usr/share/pixmaps/tdci-recovery.svg            icon
Writable data (backups, AI key, feed cache) goes to
~/.local/share/tdci-recovery/ via ftr/paths.py.
"""

import io
import tarfile
import time
import zipfile  # noqa: F401  (keeps stdlib import list honest)
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "0.4.0"
OUT = ROOT / "dist" / f"tdci-recovery_{VERSION}_all.deb"

# files that must never ship in the package
EXCLUDE_DIRS = {".git", "__pycache__", "backups", "dist", ".venv"}
EXCLUDE_FILES = {"ai_config.json", ".env", ".write_probe"}

WRAPPER = """#!/bin/sh
# TDCi Recovery launcher — opens the GUI
exec python3 /usr/share/tdci-recovery/gui_app.py "$@"
"""

DESKTOP = """[Desktop Entry]
Type=Application
Name=TDCi Recovery Diagnostics
Comment=Ford 2.0 TDCi open-source diagnostics (GUI)
Exec=tdci-recovery
Icon=tdci-recovery
Terminal=false
Categories=Utility;
Keywords=OBD;ELM327;Ford;TDCi;diagnostics;
"""

POSTINST = """#!/bin/sh
set -e
update-desktop-database /usr/share/applications 2>/dev/null || true
"""

CONTROL = """Package: tdci-recovery
Version: {ver}
Section: utils
Priority: optional
Architecture: all
Maintainer: Jo Bluemann <https://jobluemann.com>
Depends: python3, python3-tk, python3-serial
Installed-Size: {size_kb}
Description: Open-source Ford 2.0 TDCi diagnostic suite
 Backup-first OBD-II diagnostics for Ford 2.0 TDCi (Kuga Mk2, Focus Mk3):
 full module scan (incl. modules the dashboard hides), sourced known-issues
 knowledge base, forum/RSS symptom search, and a free two-model AI assistant
 with in-app key setup. GUI and CLI. Works with ELM327 USB or Bluetooth.
 Home: https://github.com/jobluemann/ford-tdci-recovery
"""


def _tar_bytes(entries):
    """entries: list of (arcname, bytes, mode). Returns gzipped tar bytes."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data, mode in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = mode
            info.mtime = int(time.time())
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _payload_entries():
    entries = []
    base = "usr/share/tdci-recovery"
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.name in EXCLUDE_FILES:
            continue
        entries.append((f"{base}/{rel.as_posix()}",
                        p.read_bytes(), 0o644))
    entries.append(("usr/local/bin/tdci-recovery", WRAPPER.encode(), 0o755))
    entries.append(("usr/share/applications/tdci-recovery.desktop",
                    DESKTOP.encode(), 0o644))
    icon = ROOT / "site" / "pwa" / "icon.svg"
    entries.append(("usr/share/pixmaps/tdci-recovery.svg",
                    icon.read_bytes(), 0o644))
    return entries


def _ar(members):
    """members: list of (name, bytes) -> classic ar archive bytes."""
    out = io.BytesIO()
    out.write(b"!<arch>\n")
    for name, data in members:
        header = (f"{name + '/':<16}{int(time.time()):<12}{0:<6}{0:<6}"
                  f"{0o100644:<8o}{len(data):<10}`\n")
        out.write(header.encode())
        out.write(data)
        if len(data) % 2:
            out.write(b"\n")
    return out.getvalue()


def main():
    payload = _payload_entries()
    size_kb = sum(len(d) for _, d, _ in payload) // 1024

    data_tar = _tar_bytes([(f"./{n}", d, m) for n, d, m in payload])
    control_tar = _tar_bytes([
        ("./control", CONTROL.format(ver=VERSION, size_kb=size_kb).encode(), 0o644),
        ("./postinst", POSTINST.encode(), 0o755),
    ])

    deb = _ar([
        ("debian-binary", b"2.0\n"),
        ("control.tar.gz", control_tar),
        ("data.tar.gz", data_tar),
    ])

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(deb)
    print(f"built {OUT} ({len(deb)} bytes, {len(payload)} payload files)")


if __name__ == "__main__":
    main()
