"""Optional AI assistant — OpenAI-compatible endpoints, stdlib only.

Provider presets (select with FTR_AI_PROVIDER, default 'ollama'):
  ollama     -> fully local, no key (localhost:11434)
  groq       -> free tier (api.groq.com)
  gemini     -> free tier via Google AI Studio
  grok       -> xAI Grok API (paid; NOT the free grok.com chat)
  openrouter -> one key, many models: gpt-*, llama, qwen, gemma, grok
  custom     -> set AI_BASE_URL yourself

Two-model pipeline (optional): a fast 'research' model analyses gathered
evidence first, then the 'diagnostics' model answers:
  FTR_RESEARCH_PROVIDER / FTR_RESEARCH_MODEL / FTR_RESEARCH_API_KEY / FTR_RESEARCH_BASE_URL
  FTR_DIAG_PROVIDER     / FTR_DIAG_MODEL     / FTR_DIAG_API_KEY     / FTR_DIAG_BASE_URL
Unset role vars fall back to FTR_AI_PROVIDER / AI_API_KEY / AI_MODEL / AI_BASE_URL.

Privacy: context is the known-issues KB plus a snapshot with the VIN REMOVED.
"""

import json
import os
import urllib.request

PROVIDERS = {
    # truly free, fully local — no key needed (run: ollama pull llama3.1:8b)
    "ollama": ("http://localhost:11434/v1", "llama3.1:8b"),
    # free tier after signup (OpenAI-compatible). Qwen on Groq is the default
    # diagnostics brain; llama-3.1-8b-instant is the fast research model.
    "groq": ("https://api.groq.com/openai/v1", "qwen/qwen3.6-27b"),
    # free tier via Google AI Studio (OpenAI-compatible endpoint)
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.0-flash"),
    # xAI Grok API — paid product (occasional free-credit promos)
    "grok": ("https://api.x.ai/v1", "grok-3-mini"),
    # one key, all the models: openai/gpt-*, meta-llama/*, qwen/*, google/gemma-*, x-ai/grok-*
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.1-8b-instruct"),
    "custom": ("", "gpt-4o-mini"),
}

# Two roles, two models (optional). If the role-specific vars are unset, both
# roles fall back to FTR_AI_PROVIDER / AI_API_KEY / AI_MODEL.
#   FTR_RESEARCH_PROVIDER / FTR_RESEARCH_MODEL / FTR_RESEARCH_API_KEY
#   FTR_DIAG_PROVIDER     / FTR_DIAG_MODEL     / FTR_DIAG_API_KEY
# Recommended FREE recipe — one Groq key (console.groq.com), two models:
#   FTR_RESEARCH_PROVIDER=groq FTR_RESEARCH_MODEL=llama-3.1-8b-instant
#   FTR_DIAG_PROVIDER=groq     FTR_DIAG_MODEL=qwen/qwen3.6-27b
#   GROQ_API_KEY=<groq key>    (shared key used by both roles)
# Alternative (one OpenRouter key, openrouter.ai — :free models exist):
#   FTR_RESEARCH_PROVIDER=openrouter FTR_RESEARCH_MODEL=meta-llama/llama-3.1-8b-instruct:free
#   FTR_DIAG_PROVIDER=openrouter     FTR_DIAG_MODEL=qwen/qwen-2.5-7b-instruct:free
#   AI_API_KEY=<openrouter key>


def _settings(role=None):
    prefix = f"FTR_{role.upper()}_" if role else ""
    provider = (os.environ.get(prefix + "PROVIDER") or
                os.environ.get("FTR_AI_PROVIDER", "ollama")).lower()
    base, model = PROVIDERS.get(provider, PROVIDERS["custom"])
    base = (os.environ.get(prefix + "BASE_URL") or
            os.environ.get("AI_BASE_URL", base)).rstrip("/")
    model = (os.environ.get(prefix + "MODEL") or
             os.environ.get("AI_MODEL", model))
    key = (os.environ.get(prefix + "API_KEY") or
           os.environ.get("AI_API_KEY", ""))
    if not key and provider == "groq":
        key = os.environ.get("GROQ_API_KEY", "")  # qwen-groq skill convention
    if provider == "ollama" and not key:
        key = "ollama"  # local server ignores it, but the header must exist
    return provider, base, model, key


def configured():
    _, base, _, key = _settings()
    return bool(base and key)


def gather_evidence(question, vehicle=None, max_kb=3, max_feed=5):
    """Auto-research step: pull KB matches + RSS/forum results for a question.

    Returns a text block injected into the AI context. Works offline (KB
    always; RSS when feeds are configured in data/feeds.json).
    """
    from . import feeds, known_issues
    parts = []
    kb = known_issues.load_kb(vehicle)
    hits = known_issues.match(kb, symptom_text=question)
    if hits:
        lines = []
        for score, issue, _, _ in hits[:max_kb]:
            lines.append(f"- {issue['title']} (known issue: {issue['known_issue']}, "
                         f"confidence {issue['confidence']}): causes: "
                         + "; ".join(issue["likely_causes"][:3])
                         + " | sources: " + "; ".join(issue.get("sources", [])[:3]))
        parts.append("KNOWN-ISSUES KB MATCHES:\n" + "\n".join(lines))
    cfg = feeds.CACHE.parent.parent / "data" / "feeds.json"
    feed_list = feeds.DEFAULT_FEEDS
    if cfg.exists():
        try:
            feed_list = json.loads(cfg.read_text(encoding="utf-8"))["feeds"]
        except (json.JSONDecodeError, KeyError):
            pass
    if feed_list:
        stop = {"the", "and", "with", "from", "that", "this", "have", "when",
                "what", "why", "how", "car", "vehicle", "ford"}
        words = [w for w in question.lower().split()
                 if len(w) > 3 and w not in stop][:3]
        if words:
            try:
                results, _ = feeds.search(feed_list, words)
                if results:
                    parts.append("FORUM/RSS RESULTS:\n" + "\n".join(
                        f"- {r['title']} ({r['link']})" for r in results[:max_feed]))
            except Exception:
                pass  # offline or feeds down — KB evidence still stands
    return "\n\n".join(parts)


def _snapshot_sanitized(path):
    try:
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
        snap.get("vehicle", {}).pop("vin", None)
        return json.dumps(snap)[:4000]
    except Exception:
        return ""


def chat(messages, kb_text="", snapshot_path=None, role="diag"):
    provider, base, model, key = _settings(role)
    if not (base and key):
        return ("AI assistant not configured. Free options: run Ollama locally "
                "(FTR_AI_PROVIDER=ollama, no key needed), or get a free key from "
                "Groq (FTR_AI_PROVIDER=groq) or Google AI Studio "
                "(FTR_AI_PROVIDER=gemini), or one OpenRouter key for many "
                "models (FTR_AI_PROVIDER=openrouter), then set AI_API_KEY. "
                "Grok: FTR_AI_PROVIDER=grok (paid API). Two-model setup: set "
                "FTR_RESEARCH_* and FTR_DIAG_* (see module docstring). The "
                "offline known-issues lookup works without any of this.")
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
                 "Authorization": f"Bearer {key}",
                 # Groq/Cloudflare rejects requests with no UA (error 1010)
                 "User-Agent": "ford-tdci-recovery/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


def chat_grounded(question, history=None, snapshot_path=None, vehicle=None):
    """Ask with auto-research: KB + RSS evidence is gathered for the question
    and injected before the model answers. Returns (reply, evidence_text).

    Two-model pipeline (optional): if FTR_RESEARCH_PROVIDER is set, a fast
    'research' model first analyses the question + evidence and extracts the
    relevant facts and which sources to trust; its notes are then handed to
    the 'diagnostics' model for the final answer. With no research provider
    configured this behaves as a single diagnostics call.
    """
    evidence = gather_evidence(question, vehicle=vehicle)

    research_notes = ""
    if os.environ.get("FTR_RESEARCH_PROVIDER"):
        research_prompt = (
            "You are the research stage of a two-model Ford 2.0 TDCi "
            "diagnostic pipeline. A separate diagnostics model will write the "
            "final answer. Your job: analyse the question and the gathered "
            "evidence below, extract the facts that matter, flag which "
            "sources are trustworthy, and list anything that should be "
            "verified on the vehicle. Be brief and technical.\n\n"
            f"QUESTION:\n{question}\n\nEVIDENCE:\n{evidence or '(none)'}"
        )
        research_notes = chat([{"role": "user", "content": research_prompt}],
                              role="research")

    grounded = question
    if evidence:
        grounded += ("\n\n[AUTO-GATHERED EVIDENCE — cite it in your answer]\n"
                     + evidence)
    if research_notes:
        grounded += ("\n\n[RESEARCH-STAGE NOTES — use as supporting analysis]\n"
                     + research_notes)
    messages = (history or []) + [{"role": "user", "content": grounded}]
    return chat(messages, snapshot_path=snapshot_path, role="diag"), evidence
