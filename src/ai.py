"""Simple AI wrapper for Stapler-y.

Behavior:
- If `ollama` package is installed,
  it will call Ollama's chat completions.
- Otherwise it falls back to a lightweight rule/canned response generator.

This module exposes a single function `get_response(prompt)` which returns a string.
"""
import os
import random
import base64
import io

# Try to use Ollama if configured
try:
    import ollama
except Exception:
    ollama = None

systemMessage = """You are Stapler-y: a helpful, friendly desktop stapler that has come to life!
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

fallbackData = [
    {
        "prompts": [
            "hello",
            "hey",
            "hi"
        ],
        "responses": [
            "Hey there! Need some help?",
            "Hello! Ready when you are."
        ]
    },
    {
        "prompts": [
            "who are you",
            "what are you",
            "your name"
        ],
        "responses": [
            "Hello, I'm Stapler-y, your personal AI Assistant!",
            "Hi! I'm Stapler-y."
        ]
    },
    {
        "prompts": [
            "you do",
            "your purpose",
            "your job",
            "why are you"
        ],
        "responses": [
            "My job is to help you anyway I can!",
            "I can help you with anything! Do you want some help?"
        ]
    }
]

def _fallback_response(prompt: str) -> str:
    # Very simple fallback: some heuristics + canned replies

    userPrompt = prompt.lower().strip()

    if not userPrompt:
        return "Say something and I'll try to help!"
    for fallbackDict in fallbackData:
        if any(word in userPrompt for word in fallbackDict["prompts"]):
            return random.choice(fallbackDict["responses"])
    
    # echo-ish with a tiny personality
    return "I heard: '" + (prompt if len(prompt) < 200 else prompt[:200] + "...") + "' — how can I help?"


def get_response(prompt: str, timeout: float = 10.0, screen_image=None) -> str:
    """Return a response for `prompt`.

    Attempts to use Ollama if available; otherwise uses a fallback.
    """
    base_dir = os.path.dirname(__file__)

    # ── Build screen context ──────────────────────────────────────────────────
    screen_context = None   # plain-text context for non-vision path
    screen_b64      = None  # base64 PNG for vision models

    if screen_image is not None:
        # Always encode the image so vision models can use it directly
        try:
            buf = io.BytesIO()
            screen_image.save(buf, format='PNG')
            screen_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception:
            screen_b64 = None

        # Also try OCR as a text fallback for non-vision models
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

            if not screen_context:
                # Save last screenshot so users can inspect it manually
                try:
                    shot_path = os.path.join(base_dir, "brain", "last_screenshot.png")
                    os.makedirs(os.path.dirname(shot_path), exist_ok=True)
                    screen_image.save(shot_path)
                    screen_context = f"[Screenshot saved to {shot_path}]"
                except Exception:
                    pass
        except Exception:
            pass

    # ── Call Ollama ───────────────────────────────────────────────────────────
    if ollama:
        model = os.environ.get("STAPLERY_OLLAMA_MODEL", "llama3")
        print(f"Using Ollama model: {model}")
        try:
            user_msg: dict = {"role": "user", "content": prompt}

            # Attach image for vision-capable models (llava, gemma3, etc.)
            # Non-vision models ignore the images field without erroring.
            if screen_b64 is not None:
                user_msg["images"] = [screen_b64]
            elif screen_context:
                user_msg["content"] = prompt + "\n\n" + screen_context

            resp = ollama.chat(
                model=model,
                messages=[{"role": "system", "content": systemMessage}, user_msg]
            )
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

    # ── Fallback ──────────────────────────────────────────────────────────────
    ctx = (screen_context or "") if screen_b64 is None else "[image attached]"
    return _fallback_response(prompt if not ctx else f"{prompt}\n\n{ctx}")

if __name__ == "__main__":
    # Quick test
    print(get_response("Hello, who are you?"))