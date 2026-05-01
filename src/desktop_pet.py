import tkinter as tk
from tkinter import Menu
import random
import math
import os
import time
from PIL import Image, ImageDraw, ImageTk, ImageOps

from chat_win import ChatWindow


class DesktopPet:
    def __init__(self):
        # Initialize window
        self.root = tk.Tk()
        self.root.title("Desktop Pet")
        
        # Configure window
        self.setup_window()
        
        # Pet properties
        self.pet_size = 128
        self.x = 400.0  # Will be set properly after screen bounds detection
        self.y = 400.0  # Will be set properly after screen bounds detection
        self.velocity_x = 0
        self.velocity_y = 0
        self.state = "idle"
        self.frame = 0
        self.direction = 1
        self.is_dead = False
        self.particles = []
        self.death_timer = 0
        
        # AI Chat
        self.chat = ChatWindow(self)
        self.is_thinking = False
        self.last_response = ""

        # Movement targets (2D)
        self.target_x = None
        self.target_y = None
        self.patrol_timer = 0
        
        # Physics
        self.max_speed = 3.5
        self.friction = 0.88  # Friction for top-down deceleration
        
        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.pet_size,
            height=self.pet_size,
            bg='white',
            highlightthickness=0,
            cursor='hand2'
        )
        self.canvas.pack()
        
        # Create sprites
        self.sprite_images = self.create_all_sprites()
        self.sprites = {}
        self.sprites_flipped = {}
        self.convert_sprites()
        
        # Interaction
        self.drag_data = {
            "offset_x": 0, "offset_y": 0,   # canvas-relative click position
            "dragging": False,
            "start_x": 0, "start_y": 0,
            # Recent positions used to compute throw velocity on release
            "prev_x": 0.0, "prev_y": 0.0,
            "prev_time": 0.0,
            "vel_x": 0.0, "vel_y": 0.0,
        }
        self.click_count = 0
        self.last_click_time = 0
        
        # Bind events
        self.bind_events()
        
        # Keyboard shortcuts
        self.root.bind('<space>', lambda e: self.chat.show_chat_dialog())

        # Screen bounds - get virtual screen size for multi-monitor support
        self.update_screen_bounds()
        
        # Set initial position to center of primary monitor
        self.x = self.primary_width // 2 - self.pet_size // 2
        self.y = self.primary_height // 2
        
        # Position window
        self.update_position()
        
        # Start loops
        self.running = True
        self.animate()
        self.update_physics()
        self.ai_loop()
        self.refresh_screen_bounds_periodically()
        
    def setup_window(self):
        """Configure window properties"""
        # Transparency
        try:
            self.root.attributes('-transparentcolor', 'white')
        except:
            pass
        
        # Always on top
        try:
            self.root.attributes('-topmost', True)
        except:
            pass
        
        # Remove window decorations
        self.root.overrideredirect(True)
        
        # Make window click-through in some areas (platform dependent)
        try:
            self.root.wm_attributes('-alpha', 0.99)  # Slightly transparent for better rendering
        except:
            pass
    
    def bind_events(self):
        """Bind all event handlers"""
        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonPress-3>", self.show_menu)
        self.canvas.bind("<Enter>", self.on_mouse_enter)
        self.canvas.bind("<Leave>", self.on_mouse_leave)
    
    def update_screen_bounds(self):
        """Update screen bounds to support multi-monitor setups"""
        # Force window to update
        self.root.update_idletasks()
        
        # Get primary screen dimensions - always store these
        self.primary_width = self.root.winfo_screenwidth()
        self.primary_height = self.root.winfo_screenheight()

        # Try platform-specific virtual screen bounds (Windows)
        try:
            import ctypes
            user32 = ctypes.windll.user32
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79

            left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

            # If values look sensible, use them
            if width > 0 and height > 0:
                self.screen_left = left
                self.screen_top = top
                self.screen_width = width
                self.screen_height = height
                return
        except Exception:
            # Not Windows or call failed; fall back to other heuristics below
            pass
        
        # Try to get virtual screen dimensions (multi-monitor)
        try:
            self.root.update()
            
            # Method 1: Try winfo_vrootwidth/height (X11)
            try:
                virt_width = self.root.winfo_vrootwidth()
                virt_height = self.root.winfo_vrootheight()
                if virt_width > self.primary_width or virt_height > self.primary_height:
                    self.screen_width = virt_width
                    self.screen_height = virt_height
                    return
            except:
                pass
            
            # Method 2: For Windows/Linux, estimate based on positioning
            test_x = self.primary_width + 100
            try:
                self.root.geometry(f'+{test_x}+100')
                self.root.update()
                actual_x = self.root.winfo_x()
                
                if actual_x > self.primary_width:
                    self.screen_left = 0
                    self.screen_top = 0
                    self.screen_width = self.primary_width * 2
                    self.screen_height = self.primary_height
                    self.root.geometry(f'+{self.x}+{self.y}')
                    return
            except:
                pass
            
        except Exception as e:
            print(f"Multi-monitor detection failed: {e}")
        
        # Fallback: use primary screen only
        self.screen_left = 0
        self.screen_top = 0
        self.screen_width = self.primary_width
        self.screen_height = self.primary_height
    
    def create_all_sprites(self):
        """Create all sprite animations"""
        sprites = {
            "idle": self.create_idle_sprites(),
            "walk": self.create_walk_sprites(),
            "run": self.create_run_sprites(),
            "sleep": self.create_sleep_sprites(),
            "happy": self.create_happy_sprites(),
            "eat": self.create_eat_sprites(),
            "sit": self.create_sit_sprites(),
            "explode": self.create_explode_sprites(),
            "dead": self.create_dead_sprites(),
            "thinking": self.create_thinking_sprites(),
        }
        return sprites
    
    def draw_base_staplery(self, draw, center, base_y, top_angle=0, scale=1.0, expression="normal"):
        """Draw the Stapler-y with given parameters"""
        # Bottom/base of the Stapler-y (the part that holds staples)
        base_w = int(50 * scale)
        base_h = int(15 * scale)
        
        # Main base body - gray/silver
        draw.rectangle([
            center - base_w, base_y + 20,
            center + base_w, base_y + 35
        ], fill='#808080', outline='#404040', width=2)
        
        # Staple chamber (darker area)
        draw.rectangle([
            center - base_w + 5, base_y + 22,
            center + base_w - 5, base_y + 33
        ], fill='#505050', outline='#303030', width=1)
        
        # Top part of the Stapler-y (the part you press down)
        top_w = int(45 * scale)
        top_h = int(12 * scale)
        
        # Calculate rotation point (hinge at back)
        hinge_x = center + base_w - 10
        hinge_y = base_y + 20
        
        angle_rad = math.radians(top_angle)
        top_offset_y = int(top_angle * 0.5)
        
        draw.rectangle([
            center - top_w, base_y + 5 - top_offset_y,
            center + top_w, base_y + 17 - top_offset_y
        ], fill='#A0A0A0', outline='#606060', width=2)
        
        # Label area (lighter gray)
        draw.rectangle([
            center - top_w + 10, base_y + 8 - top_offset_y,
            center + top_w - 10, base_y + 14 - top_offset_y
        ], fill='#C0C0C0', outline='#808080', width=1)
        
        # Expression
        if expression == "happy":
            draw.arc([center - 8, base_y + 9 - top_offset_y, center - 2, base_y + 13 - top_offset_y], 
                    0, 180, fill='#000000', width=2)
            draw.arc([center + 2, base_y + 9 - top_offset_y, center + 8, base_y + 13 - top_offset_y], 
                    0, 180, fill='#000000', width=2)
        elif expression == "sleepy":
            draw.line([center - 6, base_y + 11 - top_offset_y, center - 2, base_y + 11 - top_offset_y], 
                     fill='#000000', width=2)
            draw.line([center + 2, base_y + 11 - top_offset_y, center + 6, base_y + 11 - top_offset_y], 
                     fill='#000000', width=2)
        elif expression == "excited":
            draw.ellipse([center - 7, base_y + 9 - top_offset_y, center - 3, base_y + 13 - top_offset_y], 
                        fill='#000000')
            draw.ellipse([center + 3, base_y + 9 - top_offset_y, center + 7, base_y + 13 - top_offset_y], 
                        fill='#000000')
        else:  # normal
            draw.ellipse([center - 6, base_y + 10 - top_offset_y, center - 4, base_y + 12 - top_offset_y], 
                        fill='#000000')
            draw.ellipse([center + 4, base_y + 10 - top_offset_y, center + 6, base_y + 12 - top_offset_y], 
                        fill='#000000')
        
        # Metal details/screws
        screw_positions = [
            (center - 35, base_y + 10 - top_offset_y),
            (center + 35, base_y + 10 - top_offset_y),
            (center - 35, base_y + 27),
            (center + 35, base_y + 27)
        ]
        
        for sx, sy in screw_positions:
            draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill='#505050', outline='#303030', width=1)
            draw.line([sx - 1, sy - 1, sx + 1, sy + 1], fill='#606060', width=1)
            draw.line([sx - 1, sy + 1, sx + 1, sy - 1], fill='#606060', width=1)
        
        # Spring mechanism
        draw.line([center + base_w - 5, base_y + 20, center + base_w - 5, base_y + 10 - top_offset_y], 
                 fill='#707070', width=2)
        
        # Front nose/Stapler-y opening
        draw.rectangle([
            center - base_w - 3, base_y + 22,
            center - base_w, base_y + 33
        ], fill='#606060', outline='#303030', width=1)
        
        return base_y
    
    def create_idle_sprites(self):
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            top_angle = int(math.sin(i / 4 * math.pi * 2) * 2)
            base_y = 60
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            draw.ellipse([center - 45, base_y + 36, center + 45, base_y + 42], fill='#00000020')
            frames.append(img)
        return frames
    
    def create_walk_sprites(self):
        frames = []
        for i in range(6):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            bounce = int(abs(math.sin(i / 6 * math.pi * 2)) * 5)
            top_angle = int(math.sin(i / 3 * math.pi) * 3)
            base_y = 60 - bounce
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            leg_offset = 5 if i % 2 == 0 else -5
            draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 42], fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 35 + leg_offset, center + 35, base_y + 42 + leg_offset], fill='#606060', outline='#303030', width=1)
            draw.ellipse([center - 45, base_y + 42, center + 45, base_y + 48], fill='#00000020')
            frames.append(img)
        return frames
    
    def create_run_sprites(self):
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            bounce = int(abs(math.sin(i / 4 * math.pi * 2)) * 8)
            top_angle = int(math.sin(i / 2 * math.pi) * 5)
            tilt = 3 if i % 2 == 0 else -3
            base_y = 55 - bounce
            self.draw_base_staplery(draw, center + tilt, base_y, top_angle, 1.0, "excited")
            leg_offset = 8 if i % 2 == 0 else -8
            draw.rectangle([center - 35 + tilt, base_y + 35, center - 30 + tilt, base_y + 45 + leg_offset], fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30 + tilt, base_y + 35 - leg_offset, center + 35 + tilt, base_y + 45], fill='#606060', outline='#303030', width=1)
            for j in range(3):
                draw.line([center - 60, base_y + 15 + j * 5, center - 50, base_y + 15 + j * 5], fill='#80808080', width=2)
            draw.ellipse([center - 45 + tilt, base_y + 45, center + 45 + tilt, base_y + 51], fill='#00000020')
            frames.append(img)
        return frames
    
    def create_sleep_sprites(self):
        frames = []
        for i in range(3):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            draw.rectangle([30, 70, 95, 85], fill='#A0A0A0', outline='#606060', width=2)
            draw.rectangle([35, 72, 90, 83], fill='#C0C0C0', outline='#808080', width=1)
            draw.line([55, 77, 60, 77], fill='#000000', width=2)
            draw.line([65, 77, 70, 77], fill='#000000', width=2)
            if i == 2:
                alpha_values = ['#666666', '#999999', '#CCCCCC']
                positions = [(100, 50), (105, 40), (108, 32)]
                for j, ((x, y), color) in enumerate(zip(positions, alpha_values)):
                    draw.line([x, y, x + 6, y], fill=color, width=2)
                    draw.line([x + 6, y, x, y + 6], fill=color, width=2)
                    draw.line([x, y + 6, x + 6, y + 6], fill=color, width=2)
            draw.ellipse([25, 100, 100, 106], fill='#00000020')
            frames.append(img)
        return frames
    
    def create_happy_sprites(self):
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            base_y = 60
            top_angle = 15 if i % 2 == 0 else 0
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "happy")
            draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 42], fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 35, center + 35, base_y + 42], fill='#606060', outline='#303030', width=1)
            if i % 2 == 1:
                heart_positions = [(20, 30), (95, 35)]
                for hx, hy in heart_positions:
                    self.draw_heart(draw, hx, hy, 5, '#FF69B4')
            if i == 1:
                draw.rectangle([center - 55, base_y + 28, center - 50, base_y + 32], fill='#C0C0C0', outline='#808080', width=1)
                draw.line([center - 55, base_y + 28, center - 55, base_y + 25], fill='#C0C0C0', width=1)
                draw.line([center - 50, base_y + 28, center - 50, base_y + 25], fill='#C0C0C0', width=1)
            draw.ellipse([center - 45, base_y + 42, center + 45, base_y + 48], fill='#00000020')
            frames.append(img)
        return frames
    
    def create_eat_sprites(self):
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            base_y = 65
            top_angle = 10 if i % 2 == 0 else 5
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "happy" if i % 2 == 0 else "normal")
            draw.rectangle([center - 35, base_y + 30, center - 30, base_y + 40], fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 30, center + 35, base_y + 40], fill='#606060', outline='#303030', width=1)
            if i < 3:
                paper_x = center - 60 + i * 5
                paper_y = base_y + 20
                draw.rectangle([paper_x, paper_y, paper_x + 20, paper_y + 15], fill='#FFFFFF', outline='#CCCCCC', width=1)
                draw.line([paper_x + 5, paper_y + 5, paper_x + 5, paper_y + 10], fill='#C0C0C0', width=2)
                draw.line([paper_x + 15, paper_y + 5, paper_x + 15, paper_y + 10], fill='#C0C0C0', width=2)
            draw.ellipse([center - 45, base_y + 40, center + 45, base_y + 46], fill='#00000020')
            frames.append(img)
        return frames
    
    def create_sit_sprites(self):
        frames = []
        for i in range(2):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            base_y = 70
            top_angle = 3 + i
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            draw.rectangle([center - 35, base_y + 30, center - 30, base_y + 38], fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 30, center + 35, base_y + 38], fill='#606060', outline='#303030', width=1)
            draw.ellipse([center - 50, base_y + 38, center + 50, base_y + 44], fill='#00000020')
            frames.append(img)
        return frames
    
    def create_thinking_sprites(self):
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            base_y = 60
            top_angle = 5
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 42], fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 35, center + 35, base_y + 42], fill='#606060', outline='#303030', width=1)
            bubble_y = 25
            draw.ellipse([center - 30, bubble_y, center + 30, bubble_y + 25], fill='#FFFFFF', outline='#888888', width=2)
            draw.ellipse([center - 15, bubble_y + 22, center - 10, bubble_y + 27], fill='#FFFFFF', outline='#888888', width=1)
            draw.ellipse([center - 8, bubble_y + 28, center - 5, bubble_y + 31], fill='#FFFFFF', outline='#888888', width=1)
            dot_y = bubble_y + 12
            dot_positions = [center - 12, center, center + 12]
            for j, dot_x in enumerate(dot_positions):
                offset = int(math.sin((i + j) / 4 * math.pi * 2) * 3)
                draw.ellipse([dot_x - 3, dot_y - offset, dot_x + 3, dot_y + 6 - offset], fill='#4A90E2')
            draw.ellipse([center - 45, base_y + 42, center + 45, base_y + 48], fill='#00000020')
            frames.append(img)
        return frames
    
    def create_explode_sprites(self):
        frames = []
        center = self.pet_size // 2
        for i in range(8):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            if i < 6:
                radius = (i + 1) * 12
                colors = ['#FF4500', '#FF6347', '#FFA500', '#FFD700', '#FFFF00']
                for j, color in enumerate(colors):
                    r = radius - j * 8
                    if r > 0:
                        draw.ellipse([center - r, center - r, center + r, center + r], outline=color, width=3)
                for angle in range(0, 360, 30):
                    rad = math.radians(angle)
                    length = radius * 1.5
                    x1 = center + math.cos(rad) * 10
                    y1 = center + math.sin(rad) * 10
                    x2 = center + math.cos(rad) * length
                    y2 = center + math.sin(rad) * length
                    draw.line([x1, y1, x2, y2], fill='#FF4500', width=2)
                for _ in range(15):
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(radius * 0.5, radius * 1.2)
                    px = center + math.cos(angle) * dist
                    py = center + math.sin(angle) * dist
                    size = random.randint(2, 5)
                    color = random.choice(['#FF6B9D', '#FFB6C1', '#888888', '#FF4500'])
                    draw.ellipse([px - size, py - size, px + size, py + size], fill=color)
            if i == 0 or i == 1:
                draw.ellipse([center - 40, center - 40, center + 40, center + 40], fill='#FFFFFF')
            frames.append(img)
        return frames
    
    def create_dead_sprites(self):
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            center = self.pet_size // 2
            float_offset = int(math.sin(i / 4 * math.pi * 2) * 3)
            base_y = 50 + float_offset
            draw.rectangle([center - 45, base_y + 20, center + 45, base_y + 35], fill='#E0E0FF88', outline='#B0B0FF', width=2)
            draw.rectangle([center - 40, base_y + 5, center + 40, base_y + 17], fill='#F0F0FF88', outline='#C0C0FF', width=2)
            eye_y = base_y + 10
            draw.line([center - 15, eye_y - 2, center - 11, eye_y + 2], fill='#6495ED', width=2)
            draw.line([center - 15, eye_y + 2, center - 11, eye_y - 2], fill='#6495ED', width=2)
            draw.line([center + 11, eye_y - 2, center + 15, eye_y + 2], fill='#6495ED', width=2)
            draw.line([center + 11, eye_y + 2, center + 15, eye_y - 2], fill='#6495ED', width=2)
            halo_y = base_y - 10
            draw.ellipse([center - 25, halo_y, center + 25, halo_y + 8], outline='#FFD700', width=3)
            wisp_y = base_y + 35
            wave = int(math.sin((i + 1) / 4 * math.pi * 2) * 5)
            draw.ellipse([center - 20 + wave, wisp_y, center - 10 + wave, wisp_y + 10], fill='#E0E0FF44', outline='#B0B0FF88', width=1)
            draw.ellipse([center + 10 - wave, wisp_y + 3, center + 20 - wave, wisp_y + 13], fill='#E0E0FF44', outline='#B0B0FF88', width=1)
            if i % 2 == 0:
                draw.text([center - 10, base_y + 48], "RIP", fill='#888888')
            frames.append(img)
        return frames
    
    def draw_heart(self, draw, x, y, size, color):
        draw.ellipse([x, y, x + size, y + size], fill=color)
        draw.ellipse([x + size, y, x + size * 2, y + size], fill=color)
        draw.polygon([
            (x, y + size // 2),
            (x + size, y + size * 2),
            (x + size * 2, y + size // 2)
        ], fill=color)
    
    def convert_sprites(self):
        for state, images in self.sprite_images.items():
            self.sprites[state] = [ImageTk.PhotoImage(img) for img in images]
            flipped = [ImageOps.mirror(img) for img in images]
            self.sprites_flipped[state] = [ImageTk.PhotoImage(img) for img in flipped]
    
    def update_position(self):
        try:
            self.root.geometry(f'+{int(self.x)}+{int(self.y)}')
        except:
            pass
    
    def animate(self):
        if not self.running:
            return
        config = {
            "idle": 250, "walk": 100, "run": 80, "sleep": 600,
            "jump": 100, "fall": 150, "happy": 200, "eat": 250,
            "sit": 400, "explode": 100, "dead": 300, "thinking": 250,
        }
        delay = config.get(self.state, 200)
        if self.direction == -1 and self.state in ["walk", "run", "jump", "fall"]:
            frames = self.sprites_flipped[self.state]
        else:
            frames = self.sprites[self.state]
        if self.state == "explode":
            if self.frame < len(frames) - 1:
                self.frame += 1
        else:
            self.frame = (self.frame + 1) % len(frames)
        self.canvas.delete("all")
        if self.particles:
            self.draw_particles()
        self.current_image = frames[self.frame]
        self.canvas.create_image(0, 0, anchor='nw', image=self.current_image)
        if self.is_dead and self.state == "dead":
            time_left = max(0, 5 - self.death_timer // 20)
            self.canvas.create_text(
                self.pet_size // 2, self.pet_size - 10,
                text=f"Respawning in {time_left}...",
                fill='#888888', font=('Arial', 10)
            )
        self.root.after(delay, self.animate)
    
    def draw_particles(self):
        particles_to_remove = []
        for particle in self.particles:
            particle['vy'] += 0.5
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vx'] *= 0.98
            particle['life'] -= 1
            px = particle['x'] - self.x
            py = particle['y'] - self.y
            if 0 <= px <= self.pet_size and 0 <= py <= self.pet_size and particle['life'] > 0:
                size = particle['size']
                self.canvas.create_oval(px - size, py - size, px + size, py + size,
                                        fill=particle['color'], outline='')
            if particle['life'] <= 0:
                particles_to_remove.append(particle)
        for particle in particles_to_remove:
            self.particles.remove(particle)
    
    def update_physics(self):
        if not self.running:
            return
        screen_left = getattr(self, 'screen_left', 0)
        screen_top = getattr(self, 'screen_top', 0)
        screen_w = self.screen_width
        screen_h = self.screen_height
        
        if self.is_dead:
            self.update_position()
            self.root.after(16, self.update_physics)
            return
        
        # Stop movement while dragging
        if self.drag_data["dragging"]:
            self.velocity_x = 0
            self.velocity_y = 0
            self.root.after(16, self.update_physics)
            return
        
        # Apply friction
        self.velocity_x *= self.friction
        self.velocity_y *= self.friction
        
        # Update position
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # Screen bounds (top-down, entire screen is walkable)
        left_bound = screen_left
        right_bound = screen_left + screen_w - self.pet_size
        top_bound = screen_top
        bottom_bound = screen_top + screen_h - self.pet_size
        
        # Bounce off edges
        if self.x < left_bound:
            self.x = left_bound
            self.velocity_x = abs(self.velocity_x) * 0.3
        elif self.x > right_bound:
            self.x = right_bound
            self.velocity_x = -abs(self.velocity_x) * 0.3
        
        if self.y < top_bound:
            self.y = top_bound
            self.velocity_y = abs(self.velocity_y) * 0.3
        elif self.y > bottom_bound:
            self.y = bottom_bound
            self.velocity_y = -abs(self.velocity_y) * 0.3
        
        self.update_position()
        self.root.after(16, self.update_physics)
    
    def ai_loop(self):
        if not self.running:
            return
        if self.is_dead:
            self.death_timer += 1
            if self.death_timer > 100:
                self.respawn()
            self.root.after(50, self.ai_loop)
            return
        
        self.patrol_timer += 1
        if not self.drag_data["dragging"] and self.state not in ["happy", "eat", "thinking"]:
            if self.patrol_timer > 100 and random.random() < 0.02:
                self.patrol_timer = 0
                action = random.choices(
                    ["walk", "run", "idle", "sleep", "sit"],
                    weights=[25, 10, 30, 10, 15]
                )[0]
                if action in ["walk", "run"]:
                    self.state = action
                    left = getattr(self, 'screen_left', 0)
                    top = getattr(self, 'screen_top', 0)
                    x_low = left + 50
                    x_high = left + max(100, self.screen_width - self.pet_size - 50)
                    y_low = top + 50
                    y_high = top + max(100, self.screen_height - self.pet_size - 50)
                    if x_low >= x_high:
                        x_low = left
                        x_high = left + max(100, self.screen_width - self.pet_size)
                    if y_low >= y_high:
                        y_low = top
                        y_high = top + max(100, self.screen_height - self.pet_size)
                    self.target_x = random.randint(int(x_low), int(x_high))
                    self.target_y = random.randint(int(y_low), int(y_high))
                    self.frame = 0
                elif action in ["idle", "sleep", "sit"]:
                    self.state = action
                    self.target_x = None
                    self.target_y = None
                    self.frame = 0
            
            # Move towards target
            if self.target_x is not None and self.target_y is not None and self.state in ["walk", "run"]:
                dx = self.target_x - self.x
                dy = self.target_y - self.y
                distance = math.sqrt(dx**2 + dy**2)
                
                if distance > 10:
                    # Normalize direction and apply speed
                    speed = 3.5 if self.state == "run" else 1.8
                    self.velocity_x = (dx / distance) * speed
                    self.velocity_y = (dy / distance) * speed
                    # Update direction based on x movement for sprite flipping
                    self.direction = 1 if dx >= 0 else -1
                else:
                    self.target_x = None
                    self.target_y = None
                    self.state = "idle"
                    self.velocity_x = 0
                    self.velocity_y = 0
                    self.frame = 0
        
        self.root.after(50, self.ai_loop)
    
    def trigger_death(self):
        if self.is_dead:
            return
        self.is_dead = True
        self.state = "explode"
        self.frame = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.death_timer = 0
        center_x = self.x + self.pet_size // 2
        center_y = self.y + self.pet_size // 2
        for _ in range(30):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 15)
            self.particles.append({
                'x': center_x, 'y': center_y,
                'vx': math.cos(angle) * speed, 'vy': math.sin(angle) * speed,
                'life': random.randint(20, 40),
                'color': random.choice(['#FF6B9D', '#FFB6C1', '#FF4500', '#FFA500', '#888888']),
                'size': random.randint(2, 6)
            })
        self.root.after(800, self.become_ghost)
    
    def become_ghost(self):
        if self.is_dead:
            self.state = "dead"
            self.frame = 0
    
    def respawn(self):
        self.is_dead = False
        self.state = "idle"
        self.frame = 0
        self.death_timer = 0
        self.particles.clear()
        self.x = self.primary_width // 2 - self.pet_size // 2
        self.y = self.primary_height // 2
        self.velocity_x = 0
        self.velocity_y = 0
    
    def return_to_state(self, state):
        if self.state not in ["eat", "sleep", "thinking"]:
            self.state = state
            self.frame = 0
    
    def refresh_screen_bounds_periodically(self):
        if not self.running:
            return
        self.update_screen_bounds()
        self.root.after(30000, self.refresh_screen_bounds_periodically)

    def on_click(self, event):
        if self.is_dead:
            return
        current_time = self.root.tk.call('clock', 'milliseconds')
        if current_time - self.last_click_time < 300:
            self.click_count += 1
            if self.click_count >= 2:
                self.chat.show_chat_dialog()
                self.click_count = 0
        else:
            self.click_count = 1
        self.last_click_time = current_time
        self.drag_data["offset_x"] = event.x
        self.drag_data["offset_y"] = event.y
        self.drag_data["start_x"] = self.x
        self.drag_data["start_y"] = self.y
        self.drag_data["dragging"] = True
        self.drag_data["prev_x"] = self.x
        self.drag_data["prev_y"] = self.y
        self.drag_data["prev_time"] = time.monotonic()
        self.drag_data["vel_x"] = 0.0
        self.drag_data["vel_y"] = 0.0
        if self.state not in ["happy", "eat"]:
            self.state = "idle"
        self.target_x = None
        self.velocity_x = 0
        self.velocity_y = 0

    def on_drag(self, event):
        if not self.drag_data["dragging"]:
            return
        new_x = event.x_root - self.drag_data["offset_x"]
        new_y = event.y_root - self.drag_data["offset_y"]
        now = time.monotonic()
        dt = now - self.drag_data["prev_time"]
        if dt > 0:
            self.drag_data["vel_x"] = (new_x - self.drag_data["prev_x"]) / dt
            self.drag_data["vel_y"] = (new_y - self.drag_data["prev_y"]) / dt
        self.drag_data["prev_x"] = new_x
        self.drag_data["prev_y"] = new_y
        self.drag_data["prev_time"] = now
        self.x = new_x
        self.y = new_y
        self.update_position()

    def on_release(self, event):
        if self.drag_data["dragging"]:
            scale = 1.0 / 60.0
            self.velocity_x = self.drag_data["vel_x"] * scale
            self.velocity_y = self.drag_data["vel_y"] * scale
        self.drag_data["dragging"] = False

    def on_mouse_enter(self, event):
        if not self.drag_data["dragging"] and self.state == "idle":
            if random.random() < 0.3:
                self.state = "sit"
                self.frame = 0

    def on_mouse_leave(self, event):
        pass

    def show_menu(self, event: tk.Event):
        menu = Menu(self.root, tearoff=0)
        if self.is_dead:
            menu.add_command(label="💀 Dead!", state="disabled")
            menu.add_command(label=f"⏱️  Respawn in {max(0, 5 - self.death_timer // 20)}s", state="disabled")
            menu.add_separator()
            menu.add_command(label="⚡ Revive Now", command=self.respawn)
            menu.add_separator()
            menu.add_command(label="❌ Quit", command=self.quit_app)
        else:
            menu.add_command(label="💬 Chat with Me!", command=self.chat.show_chat_dialog)
            menu.add_separator()
            menu.add_command(label="🚶 Walk", command=self.cmd_walk)
            menu.add_command(label="🏃 Run", command=self.cmd_run)
            menu.add_command(label="🧎 Sit", command=self.cmd_sit)
            menu.add_command(label="❤️ Pet", command=self.cmd_pet)
            menu.add_command(label="😴 Sleep", command=self.cmd_sleep)
            menu.add_separator()
            menu.add_command(label="❌ Quit", command=self.quit_app)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def cmd_walk(self):
        self.state = "walk"
        self.frame = 0
        left = getattr(self, 'screen_left', 0)
        top = getattr(self, 'screen_top', 0)
        x_low = left + 50
        x_high = left + max(100, self.screen_width - self.pet_size - 50)
        y_low = top + 50
        y_high = top + max(100, self.screen_height - self.pet_size - 50)
        if x_low >= x_high:
            x_low = left
            x_high = left + max(100, self.screen_width - self.pet_size)
        if y_low >= y_high:
            y_low = top
            y_high = top + max(100, self.screen_height - self.pet_size)
        self.target_x = random.randint(int(x_low), int(x_high))
        self.target_y = random.randint(int(y_low), int(y_high))

    def cmd_run(self):
        self.state = "run"
        self.frame = 0
        left = getattr(self, 'screen_left', 0)
        top = getattr(self, 'screen_top', 0)
        x_low = left + 50
        x_high = left + max(100, self.screen_width - self.pet_size - 50)
        y_low = top + 50
        y_high = top + max(100, self.screen_height - self.pet_size - 50)
        if x_low >= x_high:
            x_low = left
            x_high = left + max(100, self.screen_width - self.pet_size)
        if y_low >= y_high:
            y_low = top
            y_high = top + max(100, self.screen_height - self.pet_size)
        self.target_x = random.randint(int(x_low), int(x_high))
        self.target_y = random.randint(int(y_low), int(y_high))

    def cmd_sit(self):
        self.state = "sit"
        self.frame = 0
        self.target_x = None
        self.target_y = None
        self.velocity_x = 0
        self.velocity_y = 0

    def cmd_pet(self):
        self.state = "happy"
        self.frame = 0
        self.target_x = None
        self.root.after(2000, lambda: self.return_to_state("idle"))

    def cmd_sleep(self):
        self.state = "sleep"
        self.frame = 0
        self.target_x = None
        self.target_y = None
        self.velocity_x = 0
        self.velocity_y = 0

    def handle_ai_command(self, cmd: dict) -> str:
        name = cmd.get('command') or ''
        args = cmd.get('args') or {}
        name_l = name.lower()
        try:
            if name_l in ('walk', 'cmd_walk'):
                self.cmd_walk(); return 'Started walking.'
            if name_l in ('run', 'cmd_run'):
                self.cmd_run(); return 'Started running.'
            if name_l in ('sit', 'cmd_sit'):
                self.cmd_sit(); return 'Sitting.'
            if name_l in ('pet', 'cmd_pet'):
                self.cmd_pet(); return 'Petted.'
            if name_l in ('sleep', 'cmd_sleep'):
                self.cmd_sleep(); return 'Sleeping.'
            if name_l in ('respawn',):
                self.respawn(); return 'Respawned.'
            if name_l in ('quit', 'exit'):
                self.quit_app(); return 'Quitting app.'
            if name_l in ('set_state',):
                state = args.get('state') or args.get('s') or ''
                if state:
                    self.state = state
                    self.frame = 0
                    return f'Set state to {state}.'
            if name_l in ('move_to', 'move', 'goto'):
                x = args.get('x')
                y = args.get('y')
                try:
                    if x is not None: self.x = float(x)
                    if y is not None: self.y = float(y)
                    self.update_position()
                    return f'Moved to {self.x},{self.y}.'
                except Exception:
                    return 'Failed to move: invalid coordinates.'
            if name_l in ('clear_history', 'clear'):
                self.chat.clear_history(); return 'Cleared history.'
            if name_l in ('view_screen', 'show_screen'):
                self.chat.show_screen_view(); return 'Opened screen viewer.'
            if name_l in ('save_screenshot', 'screenshot'):
                img = self.chat.capture_screen()
                if img:
                    import datetime
                    base = os.path.dirname(__file__)
                    path = os.path.join(base, 'brain',
                                        f'screenshot_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    img.save(path)
                    return f'Screenshot saved to {path}.'
                return 'Screenshot failed.'
            if name_l in ('say', 'speak', 'message'):
                text = args.get('text') or args.get('t') or ''
                if text:
                    self.chat.add_chat_message('Stapler-y', text, '#4A90E2')
                    return 'Posted message.'
            return f'Unknown command: {name}.'
        except Exception as e:
            return f'Error executing command {name}: {e}'

    def quit_app(self):
        self.running = False
        self.root.quit()
        try:
            self.root.destroy()
        except:
            pass

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit_app()
