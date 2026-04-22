"""Shared utilities for Stapler-y.

History persistence and AI command parsing live here so they are not
duplicated between desktop_pet.py and cli.py.
"""
import os
import json
import re
from datetime import datetime


# ---------------------------------------------------------------------------
# History file helpers
# ---------------------------------------------------------------------------

def history_file_path() -> str:
    base = os.path.dirname(__file__)
    return os.path.join(base, "brain", "history.json")


def load_history() -> list:
    path = history_file_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
            if not text:
                return []
            return json.loads(text)
    except Exception:
        return []


def save_history(entries: list) -> None:
    path = history_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def append_history(sender: str, message: str, history_ref: list | None = None) -> list:
    """Append an entry to history and persist it.

    If *history_ref* is provided it is mutated in-place (avoids a disk read).
    Returns the updated list.
    """
    entry = {
        "sender": sender,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    if history_ref is None:
        history_ref = load_history()
    history_ref.append(entry)
    save_history(history_ref)
    return history_ref


# ---------------------------------------------------------------------------
# AI message-list builder
# ---------------------------------------------------------------------------

def history_to_messages(history: list) -> list:
    """Convert persisted history entries to Ollama-style message dicts.

    Only 'You' (user) and 'Stapler-y' (assistant) entries are included;
    'System' meta-messages are skipped.
    """
    messages = []
    for entry in history:
        sender = entry.get("sender", "")
        message = entry.get("message", "")
        if not message:
            continue
        if sender == "You":
            messages.append({"role": "user", "content": message})
        elif sender == "Stapler-y":
            messages.append({"role": "assistant", "content": message})
    return messages


# ---------------------------------------------------------------------------
# AI command parsing
# ---------------------------------------------------------------------------

def parse_ai_commands(text: str) -> list:
    """Parse AI response text for embedded commands.

    Supports three formats:
    - JSON object:  {"command": "jump", "args": {...}}
    - Prefixed line: COMMAND: jump arg=val
    - Slash style:  /jump  or  /cmdjump
    Returns a list of dicts: [{"command": str, "args": dict}, ...]
    """
    cmds = []
    if not text:
        return cmds

    # JSON object (preferred)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and "command" in obj:
                cmds.append({"command": obj["command"], "args": obj.get("args", {})})
                return cmds
        except Exception:
            pass

    # Line-based fallback
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("COMMAND:"):
            parts = line[len("COMMAND:"):].strip().split()
            if parts:
                name = parts[0]
                args = {}
                for p in parts[1:]:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        args[k] = v
                cmds.append({"command": name, "args": args})
        elif line.startswith("/cmd") or line.startswith("/"):
            parts = line.split()
            if parts:
                token = parts[0]
                if token.startswith("/cmd"):
                    name = token[len("/cmd"):]
                elif token.startswith("/"):
                    name = token[1:]
                else:
                    name = token
                args = {}
                for p in parts[1:]:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        args[k] = v
                cmds.append({"command": name, "args": args})

    return cmds
