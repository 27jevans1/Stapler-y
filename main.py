import tkinter as tk
import tkinter.font as tkfont
import math
import random
import time
import threading
from tkinter import messagebox
import tkinter.simpledialog as simpledialog

from ai import get_response


class StapleryApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Staplery")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Transparent background trick (Windows): pick a color and make it transparent
        self._bg = "#ff00ff"  # magenta - used as transparent color
        try:
            self.root.wm_attributes("-transparentcolor", self._bg)
        except Exception:
            pass
        
        # Load stapler icon and keep a reference to avoid garbage collection
        # Get dimensions of the stapler icon if loaded, otherwise use defaults
        try:
            self.staplery_icon = tk.PhotoImage(file="stapleryIcon.png").subsample(2) # 1/2 size (icon file too big)
            self.width = self.staplery_icon.width()
            self.height = self.staplery_icon.height()
        except Exception:
            self.staplery_icon = None
            self.width = 220
            self.height = 120
        
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            highlightthickness=0,
            bg=self._bg,
        )
        self.canvas.pack()

        # Dragging
        self._drag_data = (0, 0)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # Click interactions
        self.canvas.bind("<Double-Button-1>", self._on_double)
        self.canvas.bind("<Button-3>", self._on_right_click)

        # Context menu
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="About Staplery", command=self._show_about)
        self.menu.add_command(label="Ask Staplery...", command=self._ask_staplery)
        self.menu.add_command(label="Hide for 30s", command=self._hide_temporarily)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self._exit)

        # Pet state
        self.angle = -20  # stapler arm angle (degrees) where 0 is closed
        self.angle_dir = 1
        self.arm_open = False
        self.last_bubble = 0

        # Speech bubble
        self.bubble_id = None

        # Messages
        self.messages = [
            "Need help stapling your docs?",
            "I can staple that for you!",
            "Click me to staple (or just say hi).",
            "Pro tip: keep pages aligned first.",
            "Staples ready. Let's go!",
        ]

        # Draw initial stapler
        self._draw_stapler()

        # small idle movement
        self._idle_dx = 0

        # Start animation loop
        self._running = True
        self._loop()

    # -- Window interaction handlers
    def _on_press(self, event: tk.Event):
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self._drag_data = (event.x_root - x, event.y_root - y)

    def _on_drag(self, event: tk.Event):
        dx, dy = self._drag_data
        new_x = event.x_root - dx
        new_y = event.y_root - dy
        self.root.geometry(f"+{new_x}+{new_y}")

    def _on_release(self, event: tk.Event):
        pass

    def _on_double(self, event: tk.Event):
        pass

    def _on_right_click(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _ask_staplery(self):
        # prompt the user for a question, call AI in background, then show bubble
        prompt = simpledialog.askstring("Ask Staplery", "Ask Staplery a question:")
        if prompt is None:
            return

        # show temporary thinking bubble
        self._show_bubble("Thinking...", duration=2000)

        def worker():
            try:
                resp = get_response(prompt)
            except Exception:
                resp = "Sorry, I couldn't think right now."

            def show():
                self._show_bubble(resp, duration=8000)

            self.root.after(50, show)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _show_about(self):
        messagebox.showinfo("About Staplery", "Staplery — your friendly desktop stapler pet.")

    def _hide_temporarily(self):
        self.root.withdraw()
        self.root.after(30000, self.root.deiconify)

    def _exit(self):
        self._running = False
        self.root.destroy()

    # -- Drawing helpers
    def _draw_stapler(self):
        self.canvas.delete("all")
        # Use loaded image if available; keep reference on self so Tk doesn't GC it.
        if self.staplery_icon:
            self.canvas.create_image(self.width // 2, self.height // 2, image=self.staplery_icon)
        else:
            # Fallback: simple stapler-like shape so user sees something
            self.canvas.create_rectangle(40, 50, 180, 80, fill="#444", outline="#222", tags="stapler")
            self.canvas.create_rectangle(60, 30, 160, 55, fill="#666", outline="#333", tags="stapler")
            self.canvas.create_oval(160, 52, 175, 67, fill="#333", outline="#222", tags="stapler")
        
        # optional speech bubble if recently shown
        if self.bubble_id:
            self._draw_bubble(self.bubble_text)

    def _draw_bubble(self, text: str):
        # bubble at upper-right with wrapping and pixel measurement
        pad = 8
        font = ("Segoe UI", 9)
        f = tkfont.Font(font=font)

        # max bubble width (leave margin)
        max_w = self.width - 40

        # simple word-wrapping using font.measure
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if f.measure(test) + pad * 2 <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)

        # compute bubble size
        text_w = max((f.measure(l) for l in lines), default=0)
        line_h = f.metrics("linespace")
        w = text_w + pad * 2
        h = line_h * len(lines) + pad * 2
        x = self.width - w - 10
        y = 5

        # background rectangle (simple rounded look can be added later)
        self.canvas.create_rectangle(x, y, x + w, y + h, fill="#ffffe0", outline="#444", width=1, tags="bubble")

        # draw each wrapped line
        for i, line in enumerate(lines):
            self.canvas.create_text(x + pad, y + pad + i * line_h, anchor=tk.NW, text=line, font=font, fill="#222", tags="bubble")

    def _show_bubble(self, text, duration=2500):
        self.bubble_text = text
        self.bubble_id = time.time()
        self._draw_stapler()
        self.root.after(duration, self._clear_bubble)

    def _clear_bubble(self):
        self.bubble_id = None
        self._draw_stapler()

    def _loop(self):
        # main animation loop; called via after
        if not self._running:
            return

        # idle wiggle
        self._idle_dx += 0.2
        wiggle = math.sin(self._idle_dx) * 2
        y = 200 + wiggle
        # move window if not being dragged
        # small random idle movement
        if random.random() < 0.01:
            # occasionally show a helpful message
            if time.time() - self.last_bubble > 6:
                self._show_bubble(random.choice(self.messages), 2500)
                self.last_bubble = time.time()

        self._draw_stapler()
        self.root.after(60, self._loop)

    def run(self):
        # initial placement bottom-right
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"+{screen_w - self.width - 10}+{screen_h - self.height - 60}")
        self.root.mainloop()


if __name__ == "__main__":
    app = StapleryApp()
    app.run()
