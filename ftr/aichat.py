"""Optional AI assistant — OpenAI-compatible endpoint, stdlib only.

Configure via environment variables (nothing is hard-coded):
  AI_BASE_URL   e.g. https://api.openai.com/v1  (or any compatible endpoint)
  AI_API_KEY    your key
  AI_MODEL      e.g. gpt-4o-mini

Privacy: the assistant context is built from the known-issues KB and a
snapshot with the VIN REMOVED. If unset, chat() explains how to configure it.
"""

import json
import os
import urllib.request


def configured():
    return bool(os.environ.get("AI_BASE_URL") and os.environ.get("AI_API_KEY"))


def _snapshot_sanitized(path):
    try:
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
        snap.get("vehicle", {}).pop("vin", None)
        return json.dumps(snap)[:4000]
    except Exception:
        return ""


def chat(messages, kb_text="", snapshot_path=None):
    if not configured():
        return ("AI assistant not configured. Set AI_BASE_URL, AI_API_KEY and "
                "AI_MODEL to any OpenAI-compatible endpoint. The offline "
                "known-issues lookup (menu 8) works without it.")
    base = os.environ["AI_BASE_URL"].rstrip("/")
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
        "model": os.environ.get("AI_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "system", "content": system}] + messages,
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ['AI_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]
