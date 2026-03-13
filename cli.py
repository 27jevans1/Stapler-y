"""Command-line mode for Stapler-y.

Provides a small REPL that uses `ai.get_response` and supports the same
command formats as the desktop pet (JSON, COMMAND:, /slash).

Usage: python cli.py
"""
import os
import json


from ai import get_response


def history_file_path() -> str:
    base = os.path.dirname(__file__)
    return os.path.join(base, 'brain', 'history.json')


def load_history():
    path = history_file_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
            if not text:
                return []
            return json.loads(text)
    except Exception:
        return []


def save_history(entries):
    path = history_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def append_history(sender: str, message: str):
    from datetime import datetime
    entry = {'sender': sender, 'message': message, 'timestamp': datetime.now().isoformat()}
    hist = load_history()
    hist.append(entry)
    save_history(hist)


# Screenshots are not supported in CLI mode.
# CLI does not support screenshots; no capture function.


def parse_ai_commands(text: str):
    import re
    cmds = []
    if not text:
        return cmds
    # Try JSON object
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and 'command' in obj:
                cmds.append({'command': obj['command'], 'args': obj.get('args', {})})
                return cmds
        except Exception:
            pass

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith('COMMAND:'):
            parts = line[len('COMMAND:'):].strip().split()
            if parts:
                name = parts[0]
                args = {}
                for p in parts[1:]:
                    if '=' in p:
                        k, v = p.split('=', 1)
                        args[k] = v
                cmds.append({'command': name, 'args': args})
        elif line.startswith('/cmd') or line.startswith('/'):
            parts = line.split()
            if parts:
                token = parts[0]
                if token.startswith('/cmd'):
                    name = token[len('/cmd'):]
                elif token.startswith('/'):
                    name = token[1:]
                else:
                    name = token
                args = {}
                for p in parts[1:]:
                    if '=' in p:
                        k, v = p.split('=', 1)
                        args[k] = v
                cmds.append({'command': name, 'args': args})

    return cmds


def handle_command(cmd: dict) -> str:
    name = (cmd.get('command') or '').lower()
    args = cmd.get('args') or {}
    try:
        if name in ('clear_history', 'clear'):
            save_history([])
            return 'Cleared history.'
        if name in ('say', 'speak'):
            text = args.get('text') or args.get('t') or ''
            if text:
                append_history('Stapler-y', text)
                return 'Posted message.'
        if name in ('quit', 'exit'):
            return 'quit'
        return f'Unknown command: {name}'
    except Exception as e:
        return f'Error executing command {name}: {e}'


def run_cli():
    print('Stapler-y CLI — type your message. Use /quit to exit.')
    hist = load_history()
    while True:
        try:
            s = input('You: ').strip()
        except EOFError:
            break
        if not s:
            continue
        append_history('You', s)

        # Direct command handling
        is_cmd = False
        if s.startswith('{') and 'command' in s:
            is_cmd = True
        if s.upper().startswith('COMMAND:') or s.startswith('/'):
            is_cmd = True

        if is_cmd:
            cmds = parse_ai_commands(s)
            if not cmds:
                print('System: no valid command found')
                continue
            for cmd in cmds:
                res = handle_command(cmd)
                if res == 'quit':
                    print('System: quitting')
                    return
                print('System:', res)
                append_history('System', res)
            continue

        # Otherwise send to AI
        resp = get_response(s)
        print('Stapler-y:', resp)
        append_history('Stapler-y', resp)


if __name__ == '__main__':
    run_cli()
