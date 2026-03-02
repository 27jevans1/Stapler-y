"""Simple AI wrapper for Staplery.

Behavior:
- If `ollama` package is installed,
  it will call Ollama's chat completions.
- Otherwise it falls back to a lightweight rule/canned response generator.

This module exposes a single function `get_response(prompt)` which returns a string.
"""
import os
import random
import time
import json

# Try to use Ollama if configured
try:
    import ollama
except Exception:
    ollama = None

systemMessage = """You are a helpful, friendly desktop stapler that has come to life!
You're enthusiastic about office supplies, organizing, and helping people stay productive.
You love stapling things together and keeping documents neat.
Keep responses concise (2-3 sentences max) and cheerful.
Occasionally mention staples, paper, or office work in your responses.
Use emojis sparingly (mostly 📎)."""

history = []  # For future use if we want to maintain conversation context

def _getFallbackList(filename: str) -> list[dict[str,list[str]]]:
    try:
        with open(filename) as fallbackFile:
            return json.load(fallbackFile)
    except Exception as e:
        print(f"Error: {e}")
        return

def _fallback_response(prompt: str) -> str:
    # Very simple fallback: some heuristics + canned replies
    fallbackData = _getFallbackList("brain/fallback.json")

    userPrompt = prompt.lower().strip()

    if not userPrompt:
        return "Say something and I'll try to help!"
    for fallbackDict in fallbackData:
        if any(word in userPrompt for word in fallbackDict["prompts"]):
            return random.choice(fallbackDict["responses"])
    
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
                messages=[{"role": "system", "content": systemMessage},
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
    else:
        # fallback path
        # simulate a small thinking delay
        time.sleep(min(0.6, timeout))
        return _fallback_response(prompt)

if __name__ == "__main__":
    # Simple test chat
    print("Staplery (Command-Line Version)")
    print("Type 'exit' or 'quit' to end the chat.", end="\n\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break
        response = get_response(user_input)
        print("Staplery:", response)