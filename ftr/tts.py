"""Text-to-speech via Groq Orpheus (free tier, same key as the AI chat).

Stdlib playback: winsound on Windows, paplay/aplay on Linux.
Falls back silently to text-only if anything is missing.
"""

import os
import json
import tempfile
import urllib.request

TTS_URL = "https://api.groq.com/openai/v1/audio/speech"
MODEL = "canopylabs/orpheus-v1-english"
DEFAULT_VOICE = "autumn"


def available():
    return bool(os.environ.get("GROQ_API_KEY") or os.environ.get("AI_API_KEY"))


def plain_english_section(reply):
    """Extract the 'IN PLAIN ENGLISH' section so voice stays short and
    non-technical; falls back to the first chunk of the reply."""
    lines = reply.split("\n")
    out, capture = [], False
    for line in lines:
        low = line.lower()
        if "plain english" in low:
            capture = True
            # content may follow the header on the same line after — or :
            for sep in ("—", ":", "-"):
                if sep in line:
                    rest = line.split(sep, 1)[1].strip()
                    if len(rest) > 20:
                        out.append(rest)
                    break
            continue
        if capture and ("technical detail" in low or "what to check" in low):
            break
        if capture and line.strip():
            out.append(line.strip())
        # models sometimes put the whole section on one line
        if capture and "technical detail" in low:
            break
    text = " ".join(out).strip()
    # cut anything from the next section heading onward (same-line layouts)
    for marker in ("2. TECHNICAL", "2. Technical", "WHAT TO CHECK",
                   "What to check"):
        if marker in text:
            text = text.split(marker, 1)[0].strip()
    return text if len(text) > 20 else reply[:400]


def synthesize(text, voice=DEFAULT_VOICE, timeout=60):
    """Return WAV bytes for the given text."""
    key = os.environ.get("GROQ_API_KEY") or os.environ.get("AI_API_KEY")
    if not key:
        raise RuntimeError("No Groq key configured — open AI Setup first.")
    body = json.dumps({
        "model": MODEL, "voice": voice, "input": text[:1200],
        "response_format": "wav",
    }).encode()
    req = urllib.request.Request(
        TTS_URL, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}",
                 "User-Agent": "ford-tdci-recovery/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def play_wav(wav_bytes):
    """Play WAV bytes — stdlib only, per-OS."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        tmp = f.name
    try:
        if os.name == "nt":
            import winsound
            winsound.PlaySound(tmp, winsound.SND_FILENAME)
            return
        # Linux: paplay (PulseAudio/PipeWire) then aplay (ALSA)
        import subprocess
        for player in (["paplay", tmp], ["aplay", "-q", tmp]):
            try:
                subprocess.run(player, check=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        raise RuntimeError("No audio player found (need paplay or aplay).")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def speak(text, voice=DEFAULT_VOICE):
    """Synthesize + play. Raises on failure; caller decides how to report."""
    play_wav(synthesize(text, voice=voice))
