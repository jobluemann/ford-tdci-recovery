"""Optional AI assistant — OpenAI-compatible endpoints, stdlib only.

Provider presets (select with FTR_AI_PROVIDER, default 'custom'):
  grok    -> xAI Grok API (https://api.x.ai/v1). Note: the xAI API is a paid
             product with occasional free-credit promotions; it is NOT the
             free grok.com chat. Any OpenAI-compatible endpoint works too.
  custom  -> set AI_BASE_URL yourself (OpenAI, local LLM, anything compatible)

Configuration via environment variables (nothing hard-coded):
  FTR_AI_PROVIDER   'grok' or 'custom'
  AI_API_KEY        your key (required)
  AI_BASE_URL       overrides the provider preset URL
  AI_MODEL          overrides the provider preset model

Privacy: context is the known-issues KB plus a snapshot with the VIN REMOVED.
"""

import json
import os
import urllib.request

PROVIDERS = {
    "grok": ("https://api.x.ai/v1", "grok-3-mini"),
    "custom": ("", "gpt-4o-mini"),
}


def _settings():
    provider = os.environ.get("FTR_AI_PROVIDER", "custom").lower()
    base, model = PROVIDERS.get(provider, PROVIDERS["custom"])
    base = os.environ.get("AI_BASE_URL", base).rstrip("/")
    model = os.environ.get("AI_MODEL", model)
    key = os.environ.get("AI_API_KEY", "")
    return provider, base, model, key


def configured():
    _, base, _, key = _settings()
    return bool(base and key)


def _snapshot_sanitized(path):
    try:
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
        snap.get("vehicle", {}).pop("vin", None)
        return json.dumps(snap)[:4000]
    except Exception:
        return ""


def chat(messages, kb_text="", snapshot_path=None):
    provider, base, model, key = _settings()
    if not (base and key):
        return ("AI assistant not configured. For Grok: set FTR_AI_PROVIDER=grok "
                "and AI_API_KEY=<your xAI key>. For any other OpenAI-compatible "
                "endpoint set AI_BASE_URL + AI_API_KEY (+ AI_MODEL). The offline "
                "known-issues lookup (menu 8) works without any of this.")
    system = (
        "You are a Ford 2.0 TDCi diagnostic assistant embedded in an open-"
        "source tool. Be technical and specific. Ground answers in the "
        "known-issues knowledge base below; say 'not in KB' rather than "
        "guessing. Never suggest emissions-system bypasses or deletes.\n\n"
        f"KNOWN ISSUES KB:\n{kb_text[:8000]}"
    )
    snap = _snapshot_sanitized(snapshot_path) if snapshot_path else ""
    if snap:
        system += f"\n\nCURRENT VEHICLE SNAPSHOT (VIN stripped):\n{snap}"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]
