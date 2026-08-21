"""Install-aware paths: git-clone vs .deb system install.

A git clone is writable, so everything (backups, saved AI config, feed
cache) stays inside the project folder — unchanged behaviour.

A .deb installs read-only under /usr/share/tdci-recovery, so writable files
move to ~/.local/share/tdci-recovery/ instead.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "tdci-recovery"


def _repo_writable():
    try:
        probe = REPO_ROOT / ".write_probe"
        probe.touch()
        probe.unlink()
        return True
    except OSError:
        return False


def user_dir():
    """User-writable app dir, created on demand."""
    d = Path(os.environ.get("XDG_DATA_HOME",
                            Path.home() / ".local" / "share")) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def backups_dir():
    d = REPO_ROOT / "backups" if _repo_writable() else user_dir() / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ai_config_path():
    if _repo_writable():
        return REPO_ROOT / "data" / "ai_config.json"
    return user_dir() / "ai_config.json"
