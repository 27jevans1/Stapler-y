"""Command-line mode for Stapler-y.

Provides a small REPL that uses `ai.get_response` and supports the same
command formats as the desktop pet (JSON, COMMAND:, /slash).

Usage: python cli.py
"""
from ai import get_response
from history import (
    load_history,
    save_history,
    append_history,
    parse_ai_commands,
)


def handle_command(cmd: dict, history: list) -> str:
    name = (cmd.get("command") or "").lower()
    args = cmd.get("args") or {}
    try:
        if name in ("clear_history", "clear"):
            save_history([])
            history.clear()
            return "Cleared history."
        if name in ("say", "speak"):
            text = args.get("text") or args.get("t") or ""
            if text:
                append_history("Stapler-y", text, history)
                return "Posted message."
        if name in ("quit", "exit"):
            return "quit"
        return f"Unknown command: {name}"
    except Exception as e:
        return f"Error executing command {name}: {e}"


def run_cli():
    print("Stapler-y CLI — type your message. Use /quit to exit.")
    history = load_history()

    while True:
        try:
            s = input("You: ").strip()
        except EOFError:
            break
        if not s:
            continue

        append_history("You", s, history)

        # Direct command handling
        is_cmd = (
            (s.startswith("{") and "command" in s)
            or s.upper().startswith("COMMAND:")
            or s.startswith("/")
        )

        if is_cmd:
            cmds = parse_ai_commands(s)
            if not cmds:
                print("System: no valid command found")
                continue
            for cmd in cmds:
                res = handle_command(cmd, history)
                if res == "quit":
                    print("System: quitting")
                    return
                print("System:", res)
                append_history("System", res, history)
            continue

        # Send to AI — pass history so it has conversation context
        resp = get_response(s, history=history)
        print("Stapler-y:", resp)
        append_history("Stapler-y", resp, history)


if __name__ == "__main__":
    run_cli()
