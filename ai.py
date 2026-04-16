"""Simple AI wrapper for Stapler-y.

Behavior:
- If `ollama` package is installed,
  it will call Ollama's chat completions.
- Otherwise it falls back to a lightweight rule/canned response generator.

This module exposes a single function `get_response(prompt)` which returns a string.
"""
import os
import random

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
    # If a screenshot image is provided, try to extract text (OCR) to include as context
    screen_context = None
    if screen_image is not None:
        try:
            # Expecting a PIL Image
            try:
                import pytesseract
            except Exception:
                pytesseract = None

            if pytesseract:
                try:
                    ocr_text = pytesseract.image_to_string(screen_image)
                    if ocr_text:
                        screen_context = "Screen OCR:\n" + ocr_text
                except Exception as e:
                    # OCR failed (maybe tesseract binary missing) - save screenshot for inspection
                    try:
                        os.makedirs("brain", exist_ok=True)
                        screenshot_path = os.path.join("brain", "last_screenshot.png")
                        screen_image.save(screenshot_path)
                        screen_context = f"[Screenshot saved at {screenshot_path}]."
                    except Exception:
                        screen_context = None
            else:
                # Save to disk so the caller/user can inspect it
                os.makedirs("brain", exist_ok=True)
                screenshot_path = os.path.join("brain", "last_screenshot.png")
                try:
                    screen_image.save(screenshot_path)
                    screen_context = f"[Screenshot saved at {screenshot_path}]."
                except Exception:
                    screen_context = None
        except Exception:
            screen_context = None

    if ollama:
        try:
            # Use Ollama's chat completion
            # If we have screen context, append it to the user message
            user_content = prompt
            if screen_context:
                user_content = prompt + "\n\n" + screen_context

            resp = ollama.chat(
                model=os.environ.get("STAPLERY_OLLAMA_MODEL", "llama3"),
                messages=[{"role": "system", "content": systemMessage},
                          {"role": "user", "content": user_content}]
            )
            text = resp.message.content.strip()
            
            if text:
                return text
            else:
                print("Ollama response was empty, falling back.")
                return _fallback_response(prompt if not screen_context else prompt + "\n\n" + (screen_context or ""))
        except Exception as e:
            print("Error calling Ollama:", e)
            return _fallback_response(prompt if not screen_context else prompt + "\n\n" + (screen_context or ""))
    else:
        print("Ollama not available, using fallback response.")
        return _fallback_response(prompt if not screen_context else prompt + "\n\n" + (screen_context or ""))

if __name__ == "__main__":
    # Simple test
    print(get_response("Hello, who are you?"))