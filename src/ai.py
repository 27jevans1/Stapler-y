"""Simple AI wrapper for Stapler-y.

Behavior:
- If `ollama` package is installed, calls Ollama's chat completions.
- Otherwise falls back to a lightweight rule/canned response generator.

Exposes a single function: get_response(prompt, history=None, screen_image=None)
"""
import os
import random
import base64
import io

try:
    import ollama
except Exception:
    ollama = None

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

from elderCore import (
    ELDER_SYSTEM_MESSAGE,
    elderToggle
)

SYSTEM_MESSAGE = """You are Stapler-y: a helpful, friendly desktop stapler that has come to life!
You're enthusiastic about office supplies, organizing, and helping people stay productive.
You love stapling things together and keeping documents neat.
Keep responses concise (2-3 sentences max) and cheerful.
Occasionally mention staples, paper, or office work in your responses.
Use emojis sparingly (mostly 📎).

You may receive a screenshot of the user's screen. If so, describe what you see
and use it to give more relevant, context-aware help.

Instructions for command output:
The agent (Stapler-y) can also issue control commands to the desktop pet process.
When you need the pet to perform an action (walk, run, jump, sit, move, clear history, save screenshot, etc.), output a JSON object ONLY, with the shape:
{"command": "name", "args": { ... }}
Example: {"command": "jump"}
Example with args: {"command":"move_to","args":{"x":200,"y":150}}
If you are providing a normal chat reply (not a command), respond with plain natural language as usual.
"""

# ---------------------------------------------------------------------------
# Fallback responses
# ---------------------------------------------------------------------------

FALLBACK_DATA = [
    {
        "prompts": ["hello", "hey", "hi"],
        "responses": [
            "Hey there! Need some help?",
            "Hello! Ready when you are.",
        ],
    },
    {
        "prompts": ["who are you", "what are you", "your name"],
        "responses": [
            "Hello, I'm Stapler-y, your personal AI Assistant!",
            "Hi! I'm Stapler-y.",
        ],
    },
    {
        "prompts": ["you do", "your purpose", "your job", "why are you"],
        "responses": [
            "My job is to help you anyway I can!",
            "I can help you with anything! Do you want some help?",
        ],
    },
]


def _fallback_response(prompt: str) -> str:
    user_prompt = prompt.lower().strip()
    if not user_prompt:
        return "Say something and I'll try to help!"
    for item in FALLBACK_DATA:
        if any(word in user_prompt for word in item["prompts"]):
            return random.choice(item["responses"])
    truncated = prompt if len(prompt) < 200 else prompt[:200] + "..."
    return f"I heard: '{truncated}' — how can I help?"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_response(
    prompt: str,
    history: list | None = None,
    screen_image=None,
) -> str:
    """Return a response for *prompt*.

    Args:
        prompt: The user's current message.
        history: Optional list of persisted history dicts
                 ({"sender": "You"|"Stapler-y", "message": str, ...}).
                 When provided the full conversation is sent to Ollama so it
                 can maintain context across turns.
        screen_image: Optional PIL Image of the user's screen.
    """
    # ── Build screen context ──────────────────────────────────────────────
    screen_context: str | None = None   # plain-text fallback for non-vision models
    screen_b64: str | None = None       # base64 PNG for vision models

    if screen_image is not None:
        try:
            buf = io.BytesIO()
            screen_image.save(buf, format="PNG")
            screen_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            screen_b64 = None

        # OCR text fallback for non-vision models
        try:
            try:
                import pytesseract
            except Exception:
                pytesseract = None

            if pytesseract:
                try:
                    ocr_text = pytesseract.image_to_string(screen_image).strip()
                    if ocr_text:
                        screen_context = "Screen OCR:\n" + ocr_text
                except Exception:
                    pass


        except Exception:
            pass

    # ── Call Ollama ───────────────────────────────────────────────────────
    if ollama:
        model = os.environ.get("STAPLERY_OLLAMA_MODEL", "llama3")
        try:
            messages = _build_messages(prompt, history, screen_context, screen_b64)

            resp = ollama.chat(model=model, messages=messages)

            # ollama >= 0.2 returns a ChatResponse object, not a plain dict
            if hasattr(resp, "message"):
                text = (resp.message.content or "").strip()
            else:
                text = resp.get("message", {}).get("content", "").strip()

            if text:
                return text
            print("Ollama response was empty, using fallback.")
        except Exception as e:
            print(f"Ollama error: {e}")

    # ── Fallback ──────────────────────────────────────────────────────────
    ctx = (screen_context or "") if screen_b64 is None else "[image attached]"
    return _fallback_response(prompt if not ctx else f"{prompt}\n\n{ctx}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_messages(
    prompt: str,
    history: list | None,
    screen_context: str | None,
    screen_b64: str | None,
) -> list:
    """Assemble the full message list to send to Ollama.

    Layout:
        [system]  SYSTEM_MESSAGE
        [user]    prior user turn          ⎫
        [asst]    prior assistant turn     ⎬  repeated for each history pair
        ...                                ⎭
        [user]    current prompt  (+ image or OCR if available)
    """
    if elderToggle:
        system_msg = ELDER_SYSTEM_MESSAGE
    else:
        system_msg = SYSTEM_MESSAGE
    messages: list = [{"role": "system", "content": system_msg}]

    # Replay conversation history (skip 'System' meta-messages)
    if history:
        for entry in history:
            sender = entry.get("sender", "")
            message = entry.get("message", "")
            if not message:
                continue
            if sender == "You":
                messages.append({"role": "user", "content": message})
            elif sender == "Stapler-y":
                messages.append({"role": "assistant", "content": message})

    # Current turn
    user_msg: dict = {"role": "user", "content": prompt}
    if screen_b64 is not None:
        user_msg["images"] = [screen_b64]
    elif screen_context:
        user_msg["content"] = f"{prompt}\n\n{screen_context}"
    messages.append(user_msg)

    return messages


if __name__ == "__main__":
    print(get_response("Hello, who are you?"))
