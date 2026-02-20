"""Simple AI wrapper for Staplery.

Behavior:
- If `openai` package is installed and `OPENAI_API_KEY` environment variable is set,
  it will call OpenAI's chat completions API.
- Otherwise it falls back to a lightweight rule/canned response generator.

This module exposes a single function `get_response(prompt)` which returns a string.
"""
import os
import random
import time

# Try to use Ollama if configured
try:
    import ollama
except Exception:
    ollama = None

def _fallback_response(prompt: str) -> str:
    # Very simple fallback: some heuristics + canned replies
    p = prompt.lower().strip()
    if not p:
        return "Say something and I'll try to help!"
    if any(w in p for w in ("staple", "stapler", "paper")):
        return random.choice([
            "Make sure pages are aligned before stapling.",
            "I recommend using the center for more stable stapling.",
            "I'm a friendly stapler — try double-clicking me to staple!",
        ])
    if any(w in p for w in ("hello", "hi", "hey")):
        return random.choice(["Hey there! Need a staple?", "Hello! Ready when you are."])
    # echo-ish with a tiny personality
    return "I heard: '" + (prompt if len(prompt) < 200 else prompt[:200] + "...") + "' — how can I help?"


def get_response(prompt: str, timeout: float = 10.0) -> str:
    """Return a response for `prompt`.

    Attempts to use Ollama if available; otherwise uses a fallback.
    """

    if ollama:
        try:
            # Use Ollama's chat completion
            resp = ollama.chat(
                model=os.environ.get("STAPLERY_OLLAMA_MODEL", "llama3"),
                messages=[{"role": "system", "content": "You are Staplery, a friendly desktop stapler assistant."},
                          {"role": "user", "content": prompt}]
            )
            text = resp.get("message", {}).get("content", "").strip()
            if text:
                return text
        except Exception:
            # fallback path
            # simulate a small thinking delay
            time.sleep(min(0.6, timeout))
            return _fallback_response(prompt)
