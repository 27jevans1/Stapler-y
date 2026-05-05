![mcol logo](stapleryIcon.png)

# Stapler-y: The modern version of Clippy

Stapler-y is a desktop pet with a chat interface and simple AI-driven behavior. It can walk around your screen, respond to commands, open a screen viewer, save screenshots, and persist chat history.

## Key features
- Desktop pet UI with animated states: walk, run, sit, pet, sleep, and respawn.
- Chat interface that persists history to `brain/history.json`.
- AI-powered responses via `ollama`, with an image or OCR fallback if `pytesseract` is available.
- Screen viewer with multi-monitor support, manual refresh, 5s auto-refresh, and save-to-file.
- AI command parsing for JSON, `COMMAND:` lines, and slash-style commands.
- Alternate text-based CLI mode in `src/cli.py`.

## Prerequisites
- Python 3.10+
- `pip` installed
- Optional: Tesseract OCR for better screen-text fallback

## Install
From the repository root:

\`\`\`powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
\`\`\`

## Run
From the repository root:

\`\`\`powershell
python src/main.py
\`\`\`

For the command-line interface instead of the desktop pet:

\`\`\`powershell
python src/cli.py
\`\`\`

## Testing
Stapler-y includes unit tests to ensure code quality. To run the tests:

\`\`\`powershell
pytest
\`\`\`

Or run specific test files:

\`\`\`powershell
pytest tests/test_history.py
pytest tests/test_ai.py
\`\`\`

## Optional setup
If you want OCR-based screen context when using a non-vision Ollama model:
- Install Tesseract from https://github.com/tesseract-ocr/tesseract
- Add the Tesseract installation folder to `PATH`

## Using the desktop pet
- Right-click the pet to open its context menu.
- Use `💬 Chat with Me!` to open the chat window.
- Use the chat input and `Send` to talk to Stapler-y.
- Use the context menu buttons like `🚶 Walk`, `🏃 Run`, `🧎 Sit`, `❤️ Pet`, `😴 Sleep`, and `❌ Quit`.
- `view_screen` or `show_screen` opens the screen viewer.

## Screen viewer
- Select a monitor if multiple displays are available.
- Refresh the capture manually.
- Enable `Auto (5s)` for an automatic refresh every 5 seconds.
- Save the current view to `brain/screenshot_<timestamp>.png`.
- The captured image is used as screen context for AI prompts when enabled.

## AI command formats
Stapler-y recognizes commands returned from the AI in three formats.

### JSON command (preferred)
\`\`\`json
{"command":"jump"}
\`\`\`

### Line-based command
\`\`\`
COMMAND: move_to x=200 y=150
\`\`\`

### Slash-style command
\`\`\`
/save_screenshot
\`\`\`

## Supported commands
- `walk`, `run`, `sit`, `pet`, `sleep`, `respawn`
- `quit`, `exit`
- `set_state state=<state>`
- `move_to x=<num> y=<num>`
- `clear_history`, `clear`
- `view_screen`, `show_screen`
- `save_screenshot`, `screenshot`
- `say text=<message>`

## How it works
- `src/desktop_pet.py` is the main GUI and pet behavior implementation.
- `src/chat_win.py` handles the chat window, screen capture, and AI interaction.
- `src/ai.py` sends prompts to Ollama when available, or returns fallback responses.
- `src/history.py` persists conversation history and parses AI commands.
- `src/main.py` is the desktop entry point.
- `src/cli.py` provides a text-mode REPL for the same command formats.

## Files of interest
- `src/desktop_pet.py` — main pet UI and command handling
- `src/chat_win.py` — chat window, screen viewer, screenshot capture
- `src/ai.py` — AI integration, image/OCR context, fallback behavior
- `src/history.py` — history persistence and command parsing
- `src/main.py` — desktop app entry point
- `src/cli.py` — command-line interface

## Troubleshooting
- If the app fails to start, verify dependencies with `pip install -r requirements.txt`.
- If screen capture fails, ensure `mss` is installed; Pillow's `ImageGrab` is a fallback.
- If OCR text is empty, install `pytesseract` and the Tesseract binary.
- If history does not save, check that `brain/history.json` is writable.

## Notes
- This project is a prototype and does not include automated tests yet.
- Packaging for distribution is not included; the repository currently targets local development and experimentation.