import os
import threading
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk
try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None
try:
    import mss
except Exception:
    mss = None

from ai import get_response
from history import append_history, load_history, parse_ai_commands, save_history


class ChatWindow:
    def __init__(self, pet):
        self.pet = pet
        self.chat_window = None
        self.chat_history = None
        self.question_entry = None
        self._history = []
        self._sv = None
        self._screen_context_enabled = False
        self._ai_monitor_index = None

    def show_chat_dialog(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return

        self.chat_window = tk.Toplevel(self.pet.root)
        self.chat_window.title("Chat with Stapler-y 📎")
        self.chat_window.geometry("420x540")
        self.chat_window.configure(bg='#F0F0F0')

        toolbar = tk.Frame(self.chat_window, bg='#E0E0E0', pady=4)
        toolbar.pack(fill=tk.X, padx=10, pady=(8, 0))

        screen_var = tk.BooleanVar(value=self._screen_context_enabled)

        def _on_screen_toggle():
            self._screen_context_enabled = screen_var.get()
            if self._screen_context_enabled:
                screen_chk.config(fg='#1B5E20', selectcolor='#C8E6C9')
            else:
                screen_chk.config(fg='#555555', selectcolor='#E0E0E0')

        screen_chk = tk.Checkbutton(
            toolbar,
            text="🖥️  Let AI see screen",
            variable=screen_var,
            command=_on_screen_toggle,
            bg='#E0E0E0',
            fg='#555555',
            selectcolor='#E0E0E0',
            activebackground='#E0E0E0',
            font=('Arial', 9),
            cursor='hand2',
        )
        screen_chk.pack(side=tk.LEFT, padx=(4, 0))

        if self._screen_context_enabled:
            screen_chk.config(fg='#1B5E20', selectcolor='#C8E6C9')

        viewer_btn = tk.Button(
            toolbar,
            text="📺  Open Viewer",
            command=self.show_screen_view,
            bg='#3D3D3D', fg='#FFFFFF',
            activebackground='#555555', activeforeground='#FFFFFF',
            relief=tk.FLAT, font=('Arial', 9), padx=8, pady=2, cursor='hand2',
        )
        viewer_btn.pack(side=tk.RIGHT, padx=(0, 4))

        history_frame = tk.Frame(self.chat_window, bg='#F0F0F0')
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 0))

        self.chat_history = tk.Text(
            history_frame, wrap=tk.WORD, bg='#FFFFFF',
            font=('Arial', 10), state=tk.DISABLED,
            relief=tk.FLAT, padx=10, pady=10
        )
        self.chat_history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._history = load_history()
        for entry in self._history:
            sender = entry.get('sender', 'You')
            message = entry.get('message', '')
            ts = entry.get('timestamp')
            color = '#2E7D32' if sender == 'You' else '#4A90E2'
            self.add_chat_message(sender, message, color=color, timestamp=ts, save=False)

        scrollbar = tk.Scrollbar(history_frame, command=self.chat_history.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_history.config(yscrollcommand=scrollbar.set)

        input_frame = tk.Frame(self.chat_window, bg='#F0F0F0')
        input_frame.pack(fill=tk.X, padx=10, pady=(4, 10))

        self.question_entry = tk.Entry(input_frame, font=('Arial', 11), relief=tk.FLAT, bg='#FFFFFF')
        self.question_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=5)
        self.question_entry.bind('<Return>', lambda e: self.ask_question())

        send_btn = tk.Button(
            input_frame, text="Ask", command=self.ask_question,
            bg='#4A90E2', fg='white', font=('Arial', 10, 'bold'),
            relief=tk.FLAT, padx=15, cursor='hand2'
        )
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        clear_btn = tk.Button(
            input_frame, text="Clear", command=self.clear_history_prompt,
            bg='#E53935', fg='white', font=('Arial', 10),
            relief=tk.FLAT, padx=10, cursor='hand2'
        )
        clear_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.question_entry.focus()

    def add_chat_message(self, sender, message, color="#000000", timestamp=None, save=True):
        if not self.chat_history:
            return
        if timestamp:
            try:
                from datetime import datetime
                ts_dt = datetime.fromisoformat(timestamp)
                timestamp_display = ts_dt.strftime("%H:%M")
            except Exception:
                timestamp_display = str(timestamp)
        else:
            from datetime import datetime
            timestamp_display = datetime.now().strftime("%H:%M")

        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"\n{sender} ", f"sender_{sender}")
        self.chat_history.tag_config(f"sender_{sender}", foreground=color, font=('Arial', 10, 'bold'))
        self.chat_history.insert(tk.END, f"({timestamp_display})\n", "timestamp")
        self.chat_history.tag_config("timestamp", foreground="#888888", font=('Arial', 8))
        self.chat_history.insert(tk.END, f"{message}\n", "message")
        self.chat_history.tag_config("message", font=('Arial', 10))
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.see(tk.END)

        if save:
            self.append_history(sender, message)

    def clear_history_prompt(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear the chat history? This cannot be undone."):
            self.clear_history()

    def clear_history(self):
        try:
            self._history = []
            save_history([])
        except Exception as e:
            print(f"Failed to clear history: {e}")
        if self.chat_history:
            try:
                self.chat_history.config(state=tk.NORMAL)
                self.chat_history.delete('1.0', tk.END)
                self.chat_history.config(state=tk.DISABLED)
            except Exception:
                pass

    def append_history(self, sender: str, message: str) -> None:
        if self._history is None:
            self._history = load_history()
        append_history(sender, message, self._history)

    def ask_question(self):
        if not self.question_entry:
            return
        question = self.question_entry.get().strip()
        if not question:
            return
        self.question_entry.delete(0, tk.END)
        self.add_chat_message("You", question, "#2E7D32")

        raw = question.strip()
        is_direct_cmd = (
            (raw.startswith('{') and 'command' in raw)
            or raw.upper().startswith('COMMAND:')
            or raw.startswith('/')
            or raw.startswith('/cmd')
        )

        if is_direct_cmd:
            try:
                cmds = parse_ai_commands(question)
                if not cmds:
                    self.add_chat_message('System', 'No valid command found in input.', '#888888')
                    return
                for cmd in cmds:
                    result = self.pet.handle_ai_command(cmd)
                    self.add_chat_message('System', result, '#888888')
            except Exception as e:
                self.add_chat_message('System', f'Error running command: {e}', '#888888')
            return

        self.pet.state = "thinking"
        self.pet.is_thinking = True
        self.pet.frame = 0
        self.pet.root.after(100, lambda: self.get_ai_response(question))

    def get_ai_response(self, question):
        screen_img = None
        if self._screen_context_enabled:
            try:
                screen_img = self.capture_screen(monitor_index=self._ai_monitor_index)
            except Exception:
                screen_img = None

        history_snapshot = list(self._history)

        def worker():
            try:
                answer = get_response(question, history=history_snapshot, screen_image=screen_img)
            except Exception as e:
                answer = f"Oops, something went wrong 📎 ({e})"
            self.pet.root.after(0, lambda: self._on_ai_response(answer))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ai_response(self, answer):
        self.pet.last_response = answer
        self.add_chat_message("Stapler-y", answer, "#4A90E2")
        try:
            commands = parse_ai_commands(answer)
            for cmd in commands:
                result = self.pet.handle_ai_command(cmd)
                if result:
                    self.add_chat_message("System", result, "#888888")
        except Exception as e:
            print(f"Error handling AI commands: {e}")
        self.pet.state = "happy"
        self.pet.root.after(2000, lambda: self.pet.return_to_state("idle"))
        self.pet.is_thinking = False

    def show_screen_view(self):
        sv = getattr(self, '_sv', None)
        if sv and sv.get('win') and sv['win'].winfo_exists():
            sv['win'].lift()
            self._sv_capture()
            return

        win = tk.Toplevel(self.pet.root)
        win.title("Screen View 🖥️")
        win.geometry("900x620")
        win.configure(bg='#1E1E1E')

        monitors = self.get_monitor_list()
        first_idx = monitors[0][1] if monitors else None
        sv = {
            'win': win, 'monitor_idx': first_idx, 'auto': False,
            'auto_job': None, 'last_img': None, 'photo': None,
        }
        self._sv = sv
        self._ai_monitor_index = first_idx

        toolbar = tk.Frame(win, bg='#2D2D2D', pady=5)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        def _tbtn(text, cmd):
            b = tk.Button(toolbar, text=text, command=cmd,
                          bg='#3D3D3D', fg='#FFFFFF',
                          activebackground='#555555', activeforeground='#FFFFFF',
                          relief=tk.FLAT, font=('Arial', 9), padx=10, pady=3, cursor='hand2')
            b.pack(side=tk.LEFT, padx=3)
            return b

        if len(monitors) > 1:
            tk.Label(toolbar, text="Monitor:", bg='#2D2D2D', fg='#AAAAAA',
                     font=('Arial', 9)).pack(side=tk.LEFT, padx=(8, 2))
            mon_labels = [m[0] for m in monitors]
            mon_indices = [m[1] for m in monitors]
            mon_var = tk.StringVar(value=mon_labels[0])

            def _on_monitor_change(*_):
                idx = mon_labels.index(mon_var.get())
                sv['monitor_idx'] = mon_indices[idx]
                self._ai_monitor_index = mon_indices[idx]
                self._sv_capture()

            om = tk.OptionMenu(toolbar, mon_var, *mon_labels, command=lambda _: _on_monitor_change())
            om.config(bg='#3D3D3D', fg='#FFFFFF', activebackground='#555555',
                      activeforeground='#FFFFFF', relief=tk.FLAT,
                      font=('Arial', 9), highlightthickness=0, width=28)
            om['menu'].config(bg='#3D3D3D', fg='#FFFFFF', activebackground='#555555', activeforeground='#FFFFFF')
            om.pack(side=tk.LEFT, padx=(0, 6))
            tk.Frame(toolbar, width=1, bg='#555555').pack(side=tk.LEFT, fill=tk.Y, padx=4)

        _tbtn("🔄  Refresh", self._sv_capture)

        auto_var = tk.BooleanVar(value=False)
        auto_chk = tk.Checkbutton(
            toolbar, text="⏱  Auto (5s)", variable=auto_var,
            command=lambda: self._sv_set_auto(auto_var.get()),
            bg='#2D2D2D', fg='#AAAAAA', selectcolor='#444444',
            activebackground='#2D2D2D', activeforeground='#FFFFFF',
            font=('Arial', 9), cursor='hand2')
        auto_chk.pack(side=tk.LEFT, padx=4)

        _tbtn("💾  Save", self._sv_save)

        tk.Button(toolbar, text="✕  Close", command=win.destroy,
                  bg='#8B0000', fg='#FFFFFF',
                  activebackground='#B22222', activeforeground='#FFFFFF',
                  relief=tk.FLAT, font=('Arial', 9), padx=10, pady=3, cursor='hand2').pack(side=tk.RIGHT, padx=6)

        img_frame = tk.Frame(win, bg='#1E1E1E')
        img_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))

        img_lbl = tk.Label(img_frame, bg='#1E1E1E', text="Capturing…", fg='#666666', font=('Arial', 13))
        img_lbl.pack(fill=tk.BOTH, expand=True)
        sv['img_lbl'] = img_lbl

        status = tk.Label(win, text="", bg='#2D2D2D', fg='#777777',
                          font=('Arial', 8), anchor='w', padx=10, pady=3)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        sv['status'] = status

        def _on_close():
            self._sv_set_auto(False)
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_close)

        self._sv_capture()

    def _sv_capture(self):
        sv = getattr(self, '_sv', None)
        if not sv or not sv['win'].winfo_exists():
            return
        sv['img_lbl'].config(text="Capturing…", image='')
        sv['status'].config(text="  Capturing screen…")
        monitor_idx = sv['monitor_idx']

        def worker():
            img = self.capture_screen(monitor_index=monitor_idx)
            self.pet.root.after(0, lambda: self._sv_update(img))

        threading.Thread(target=worker, daemon=True).start()

    def _sv_update(self, img):
        from datetime import datetime
        sv = getattr(self, '_sv', None)
        if not sv or not sv['win'].winfo_exists():
            return
        if img is None:
            sv['img_lbl'].config(text="Screen capture failed.", image='')
            sv['status'].config(text="  Capture failed — is mss or Pillow installed?")
            return
        sv['last_img'] = img
        win = sv['win']
        win.update_idletasks()
        max_w = max(200, win.winfo_width() - 16)
        max_h = max(150, win.winfo_height() - 80)
        img_w, img_h = img.size
        scale = min(1.0, max_w / img_w, max_h / img_h)
        disp_w, disp_h = int(img_w * scale), int(img_h * scale)
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = getattr(Image, 'LANCZOS', Image.BICUBIC)
        photo = ImageTk.PhotoImage(img.resize((disp_w, disp_h), resample))
        sv['photo'] = photo
        sv['img_lbl'].config(image=photo, text='')
        ts = datetime.now().strftime("%H:%M:%S")
        sv['status'].config(
            text=f"  Source: {img_w}×{img_h}  →  displayed at {disp_w}×{disp_h}  ·  Captured at {ts}"
        )

    def _sv_set_auto(self, enabled: bool):
        sv = getattr(self, '_sv', None)
        if not sv:
            return
        sv['auto'] = enabled
        if sv.get('auto_job'):
            try:
                self.pet.root.after_cancel(sv['auto_job'])
            except Exception:
                pass
            sv['auto_job'] = None
        if enabled:
            self._sv_schedule_auto()

    def _sv_schedule_auto(self):
        sv = getattr(self, '_sv', None)
        if not sv or not sv.get('auto'):
            return
        if not sv['win'].winfo_exists():
            sv['auto'] = False
            return

        def tick():
            self._sv_capture()
            self._sv_schedule_auto()

        sv['auto_job'] = self.pet.root.after(5000, tick)

    def _sv_save(self):
        sv = getattr(self, '_sv', None)
        if not sv or sv.get('last_img') is None:
            return
        try:
            import datetime as dt
            base = os.path.dirname(__file__)
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(base, 'brain', f'screenshot_{stamp}.png')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            sv['last_img'].save(path)
            sv['status'].config(text=f"  Saved → {path}")
        except Exception as e:
            sv['status'].config(text=f"  Save failed: {e}")

    def capture_screen(self, monitor_index=None):
        try:
            if mss:
                with mss.mss() as sct:
                    if monitor_index is not None:
                        monitors = sct.monitors
                        idx = max(0, min(monitor_index, len(monitors) - 1))
                        monitor = monitors[idx]
                    else:
                        left = getattr(self.pet, 'screen_left', None)
                        top = getattr(self.pet, 'screen_top', None)
                        w = getattr(self.pet, 'screen_width', None)
                        h = getattr(self.pet, 'screen_height', None)
                        if None not in (left, top, w, h):
                            monitor = {'left': int(left), 'top': int(top), 'width': int(w), 'height': int(h)}
                        else:
                            monitor = sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    return Image.frombytes('RGB', sct_img.size, sct_img.rgb)
            if ImageGrab:
                left = getattr(self.pet, 'screen_left', None)
                top = getattr(self.pet, 'screen_top', None)
                w = getattr(self.pet, 'screen_width', None)
                h = getattr(self.pet, 'screen_height', None)
                if None not in (left, top, w, h):
                    return ImageGrab.grab(bbox=(int(left), int(top), int(left + w), int(top + h)))
                return ImageGrab.grab()
            return None
        except Exception as e:
            print(f"Failed to capture screen: {e}")
            return None

    def get_monitor_list(self):
        if mss:
            try:
                with mss.mss() as sct:
                    result = []
                    for i, m in enumerate(sct.monitors):
                        if i == 0:
                            label = f"All Monitors  ({m['width']}×{m['height']})"
                        else:
                            label = f"Monitor {i}  ({m['width']}×{m['height']})"
                        result.append((label, i))
                    return result
            except Exception:
                pass
        return [("Primary Screen", None)]
