"""AI setup persistence — so users never touch environment variables.

Settings are saved to data/ai_config.json (gitignored) by the GUI's
"AI Setup" dialog. On startup, apply() pushes them into os.environ where
aichat.py picks them up. Environment variables still win if both are set
(developers can override the saved file).
"""

import json
import os
from pathlib import Path

from . import paths

CONFIG_PATH = paths.ai_config_path()

# Free, current Groq models (llama-3.1-8b-instant was shut down 2026-08-16):
DEFAULT_RESEARCH_MODEL = "openai/gpt-oss-20b"   # fast stage
DEFAULT_DIAG_MODEL = "qwen/qwen3.6-27b"         # reasoning stage

_ENV_KEYS = ("FTR_AI_PROVIDER", "GROQ_API_KEY", "AI_API_KEY",
             "FTR_RESEARCH_PROVIDER", "FTR_RESEARCH_MODEL",
             "FTR_DIAG_PROVIDER", "FTR_DIAG_MODEL")


def load():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def apply(cfg=None, force=False):
    """Push saved settings into os.environ.

    By default, variables already set in the environment win (developers can
    override the saved file). With force=True the given config overwrites
    in-memory values too — required when the user saves a NEW key in the GUI
    during a running session, otherwise a previously applied (possibly bad)
    key would keep being used.
    """
    cfg = cfg if cfg is not None else load()
    for k in _ENV_KEYS:
        if cfg.get(k) and (force or not os.environ.get(k)):
            os.environ[k] = cfg[k]


def configured():
    """True if a provider + key are available from either source."""
    cfg = load()
    provider = os.environ.get("FTR_AI_PROVIDER") or cfg.get("FTR_AI_PROVIDER", "")
    key = (os.environ.get("AI_API_KEY") or os.environ.get("GROQ_API_KEY")
           or cfg.get("AI_API_KEY") or cfg.get("GROQ_API_KEY", ""))
    if provider == "ollama":
        return True
    return bool(provider and key)
