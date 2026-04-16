import tkinter as tk
from tkinter import Menu, messagebox
import random
import math
import os
import json
import re
import threading
import time
from PIL import Image, ImageDraw, ImageTk, ImageOps
try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None
try:
    import mss
except Exception:
    mss = None

from ai import get_response


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
        self.on_ground = False
        self.is_dead = False
        self.particles = []
        self.death_timer = 0
        
        # Personality stats
        self.energy = 100
        self.happiness = 80
        self.hunger = 50
        
        # AI Chat
        self.chat_window = None
        self.is_thinking = False
        self.last_response = ""
        
        # Movement targets
        self.target_x = None
        self.target_y = None
        self.patrol_timer = 0
        
        # Physics
        self.gravity = 0.8
        self.friction = 0.93  # Very high friction - slows down quickly
        
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
        self.root.bind('<space>', lambda e: self.show_chat_dialog())
        self.root.bind('<c>', lambda e: self.show_chat_dialog())
        
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
            # On Windows/Linux, try to get virtual screen size
            self.root.update()
            
            # Get the root window's screen
            # Virtual screen includes all monitors
            # We'll use a trick: try to get the maximum coordinates
            
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
            # Try to move window to extreme position and see if it works
            test_x = self.primary_width + 100
            try:
                self.root.geometry(f'+{test_x}+100')
                self.root.update()
                actual_x = self.root.winfo_x()
                
                # If window moved beyond primary screen, multi-monitor exists
                if actual_x > self.primary_width:
                    # Estimate total width (common setups: 2x monitors side-by-side)
                    # Estimate virtual width as two primaries (best-effort)
                    self.screen_left = 0
                    self.screen_top = 0
                    self.screen_width = self.primary_width * 2
                    self.screen_height = self.primary_height
                    # Move back
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
            "jump": self.create_jump_sprites(),
            "fall": self.create_fall_sprites(),
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
        # This rotates based on top_angle
        top_w = int(45 * scale)
        top_h = int(12 * scale)
        
        # Calculate rotation point (hinge at back)
        hinge_x = center + base_w - 10
        hinge_y = base_y + 20
        
        # Top part - slightly angled
        import math
        angle_rad = math.radians(top_angle)
        
        # Draw top part as rectangle (simplified - not fully rotated for now)
        top_offset_y = int(top_angle * 0.5)  # Simple approximation
        
        draw.rectangle([
            center - top_w, base_y + 5 - top_offset_y,
            center + top_w, base_y + 17 - top_offset_y
        ], fill='#A0A0A0', outline='#606060', width=2)
        
        # Label area (lighter gray)
        draw.rectangle([
            center - top_w + 10, base_y + 8 - top_offset_y,
            center + top_w - 10, base_y + 14 - top_offset_y
        ], fill='#C0C0C0', outline='#808080', width=1)
        
        # Brand name or face
        if expression == "happy":
            # Happy face - smiley
            draw.arc([center - 8, base_y + 9 - top_offset_y, center - 2, base_y + 13 - top_offset_y], 
                    0, 180, fill='#000000', width=2)
            draw.arc([center + 2, base_y + 9 - top_offset_y, center + 8, base_y + 13 - top_offset_y], 
                    0, 180, fill='#000000', width=2)
        elif expression == "sleepy":
            # Closed eyes
            draw.line([center - 6, base_y + 11 - top_offset_y, center - 2, base_y + 11 - top_offset_y], 
                     fill='#000000', width=2)
            draw.line([center + 2, base_y + 11 - top_offset_y, center + 6, base_y + 11 - top_offset_y], 
                     fill='#000000', width=2)
        elif expression == "excited":
            # Wide eyes
            draw.ellipse([center - 7, base_y + 9 - top_offset_y, center - 3, base_y + 13 - top_offset_y], 
                        fill='#000000')
            draw.ellipse([center + 3, base_y + 9 - top_offset_y, center + 7, base_y + 13 - top_offset_y], 
                        fill='#000000')
        else:  # normal
            # Normal eyes - two dots
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
        
        # Spring mechanism (visible on side)
        draw.line([center + base_w - 5, base_y + 20, center + base_w - 5, base_y + 10 - top_offset_y], 
                 fill='#707070', width=2)
        
        # Front nose/Stapler-y opening
        draw.rectangle([
            center - base_w - 3, base_y + 22,
            center - base_w, base_y + 33
        ], fill='#606060', outline='#303030', width=1)
        
        return base_y
    
    def create_idle_sprites(self):
        """Create idle animation (slight movement)"""
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            top_angle = int(math.sin(i / 4 * math.pi * 2) * 2)  # Slight opening/closing
            
            base_y = 60
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            
            # Shadow
            draw.ellipse([center - 45, base_y + 36, center + 45, base_y + 42], 
                        fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_walk_sprites(self):
        """Create walking animation (bouncing/hopping)"""
        frames = []
        for i in range(6):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            bounce = int(abs(math.sin(i / 6 * math.pi * 2)) * 5)
            top_angle = int(math.sin(i / 3 * math.pi) * 3)
            
            base_y = 60 - bounce
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            
            # Little "feet" or legs (small rectangles)
            leg_offset = 5 if i % 2 == 0 else -5
            draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 42], 
                          fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 35 + leg_offset, center + 35, base_y + 42 + leg_offset], 
                          fill='#606060', outline='#303030', width=1)
            
            # Shadow
            draw.ellipse([center - 45, base_y + 42, center + 45, base_y + 48], 
                        fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_run_sprites(self):
        """Create running animation (faster bouncing)"""
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
            
            # Fast moving legs
            leg_offset = 8 if i % 2 == 0 else -8
            draw.rectangle([center - 35 + tilt, base_y + 35, center - 30 + tilt, base_y + 45 + leg_offset], 
                          fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30 + tilt, base_y + 35 - leg_offset, center + 35 + tilt, base_y + 45], 
                          fill='#606060', outline='#303030', width=1)
            
            # Motion lines
            for j in range(3):
                draw.line([center - 60, base_y + 15 + j * 5, center - 50, base_y + 15 + j * 5], 
                         fill='#80808080', width=2)
            
            # Shadow
            draw.ellipse([center - 45 + tilt, base_y + 45, center + 45 + tilt, base_y + 51], 
                        fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_sleep_sprites(self):
        """Create sleeping animation"""
        frames = []
        for i in range(3):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            
            # Stapler-y lying down (rotated 90 degrees)
            # Draw as horizontal rectangle
            draw.rectangle([30, 70, 95, 85], fill='#A0A0A0', outline='#606060', width=2)
            draw.rectangle([35, 72, 90, 83], fill='#C0C0C0', outline='#808080', width=1)
            
            # Sleepy face
            draw.line([55, 77, 60, 77], fill='#000000', width=2)
            draw.line([65, 77, 70, 77], fill='#000000', width=2)
            
            # Z's (animated)
            if i == 2:
                alpha_values = ['#666666', '#999999', '#CCCCCC']
                positions = [(100, 50), (105, 40), (108, 32)]
                
                for j, ((x, y), color) in enumerate(zip(positions, alpha_values)):
                    # Draw Z
                    draw.line([x, y, x + 6, y], fill=color, width=2)
                    draw.line([x + 6, y, x, y + 6], fill=color, width=2)
                    draw.line([x, y + 6, x + 6, y + 6], fill=color, width=2)
            
            # Shadow
            draw.ellipse([25, 100, 100, 106], fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_jump_sprites(self):
        """Create jump animation"""
        frames = []
        jump_phases = [0, -15, -25, -20, -10, 0]
        
        for i, jump_y in enumerate(jump_phases):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            base_y = 60 + jump_y
            
            # Open wider when jumping
            top_angle = 10 if jump_y < -10 else 3
            expression = "excited" if jump_y < -10 else "normal"
            
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, expression)
            
            # Legs extended when jumping
            if i <= 1:  # Crouch
                draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 40], 
                              fill='#606060', outline='#303030', width=1)
                draw.rectangle([center + 30, base_y + 35, center + 35, base_y + 40], 
                              fill='#606060', outline='#303030', width=1)
            else:  # In air/landing
                draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 45], 
                              fill='#606060', outline='#303030', width=1)
                draw.rectangle([center + 30, base_y + 35, center + 35, base_y + 45], 
                              fill='#606060', outline='#303030', width=1)
            
            # Shadow
            shadow_size = 40 - abs(jump_y) // 2
            draw.ellipse([center - shadow_size, 95, center + shadow_size, 101], 
                        fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_fall_sprites(self):
        """Create falling animation"""
        frames = []
        for i in range(2):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            base_y = 55
            
            # Wide open when falling
            top_angle = 15 if i == 0 else 12
            
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            
            # Legs dangling
            wobble = 3 if i == 0 else -3
            draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 48], 
                          fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30 + wobble, base_y + 35, center + 35 + wobble, base_y + 48], 
                          fill='#606060', outline='#303030', width=1)
            
            frames.append(img)
        return frames
    
    def create_happy_sprites(self):
        """Create happy animation (stapling action)"""
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            base_y = 60
            
            # Rapid opening/closing like stapling
            top_angle = 15 if i % 2 == 0 else 0
            
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "happy")
            
            # Legs
            draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 42], 
                          fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 35, center + 35, base_y + 42], 
                          fill='#606060', outline='#303030', width=1)
            
            # Hearts
            if i % 2 == 1:
                heart_positions = [(20, 30), (95, 35)]
                for hx, hy in heart_positions:
                    self.draw_heart(draw, hx, hy, 5, '#FF69B4')
            
            # Staples coming out!
            if i == 1:
                draw.rectangle([center - 55, base_y + 28, center - 50, base_y + 32], 
                              fill='#C0C0C0', outline='#808080', width=1)
                draw.line([center - 55, base_y + 28, center - 55, base_y + 25], 
                         fill='#C0C0C0', width=1)
                draw.line([center - 50, base_y + 28, center - 50, base_y + 25], 
                         fill='#C0C0C0', width=1)
            
            # Shadow
            draw.ellipse([center - 45, base_y + 42, center + 45, base_y + 48], 
                        fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_eat_sprites(self):
        """Create eating animation (consuming paper/staples)"""
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            base_y = 65
            
            # Opening to eat
            top_angle = 10 if i % 2 == 0 else 5
            
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "happy" if i % 2 == 0 else "normal")
            
            # Legs
            draw.rectangle([center - 35, base_y + 30, center - 30, base_y + 40], 
                          fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 30, center + 35, base_y + 40], 
                          fill='#606060', outline='#303030', width=1)
            
            # Paper/staples being consumed
            if i < 3:
                paper_x = center - 60 + i * 5
                paper_y = base_y + 20
                draw.rectangle([paper_x, paper_y, paper_x + 20, paper_y + 15], 
                              fill='#FFFFFF', outline='#CCCCCC', width=1)
                # Staples on paper
                draw.line([paper_x + 5, paper_y + 5, paper_x + 5, paper_y + 10], 
                         fill='#C0C0C0', width=2)
                draw.line([paper_x + 15, paper_y + 5, paper_x + 15, paper_y + 10], 
                         fill='#C0C0C0', width=2)
            
            # Shadow
            draw.ellipse([center - 45, base_y + 40, center + 45, base_y + 46], 
                        fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_sit_sprites(self):
        """Create sitting animation"""
        frames = []
        for i in range(2):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            base_y = 70  # Lower when sitting
            
            # Slightly more open when sitting
            top_angle = 3 + i
            
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            
            # Legs tucked in
            draw.rectangle([center - 35, base_y + 30, center - 30, base_y + 38], 
                          fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 30, center + 35, base_y + 38], 
                          fill='#606060', outline='#303030', width=1)
            
            # Shadow (larger when sitting)
            draw.ellipse([center - 50, base_y + 38, center + 50, base_y + 44], 
                        fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_thinking_sprites(self):
        """Create thinking animation (with thought bubble dots)"""
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            base_y = 60
            
            # Slightly tilted when thinking
            top_angle = 5
            
            self.draw_base_staplery(draw, center, base_y, top_angle, 1.0, "normal")
            
            # Legs
            draw.rectangle([center - 35, base_y + 35, center - 30, base_y + 42], 
                          fill='#606060', outline='#303030', width=1)
            draw.rectangle([center + 30, base_y + 35, center + 35, base_y + 42], 
                          fill='#606060', outline='#303030', width=1)
            
            # Thought bubble with dots
            bubble_y = 25
            
            # Main bubble
            draw.ellipse([center - 30, bubble_y, center + 30, bubble_y + 25], 
                        fill='#FFFFFF', outline='#888888', width=2)
            
            # Small connector bubbles
            draw.ellipse([center - 15, bubble_y + 22, center - 10, bubble_y + 27], 
                        fill='#FFFFFF', outline='#888888', width=1)
            draw.ellipse([center - 8, bubble_y + 28, center - 5, bubble_y + 31], 
                        fill='#FFFFFF', outline='#888888', width=1)
            
            # Animated dots in bubble
            dot_y = bubble_y + 12
            dot_positions = [center - 12, center, center + 12]
            for j, dot_x in enumerate(dot_positions):
                # Bounce dots in sequence
                offset = int(math.sin((i + j) / 4 * math.pi * 2) * 3)
                draw.ellipse([dot_x - 3, dot_y - offset, dot_x + 3, dot_y + 6 - offset], 
                            fill='#4A90E2')
            
            # Shadow
            draw.ellipse([center - 45, base_y + 42, center + 45, base_y + 48], 
                        fill='#00000020')
            
            frames.append(img)
        return frames
    
    def create_explode_sprites(self):
        """Create explosion animation"""
        frames = []
        center = self.pet_size // 2
        
        for i in range(8):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Explosion circles expanding
            if i < 6:
                radius = (i + 1) * 12
                # Multiple explosion circles
                colors = ['#FF4500', '#FF6347', '#FFA500', '#FFD700', '#FFFF00']
                for j, color in enumerate(colors):
                    r = radius - j * 8
                    if r > 0:
                        alpha = int(255 * (1 - i / 6))
                        draw.ellipse([
                            center - r, center - r,
                            center + r, center + r
                        ], outline=color, width=3)
                
                # Impact lines/rays
                for angle in range(0, 360, 30):
                    rad = math.radians(angle)
                    length = radius * 1.5
                    x1 = center + math.cos(rad) * 10
                    y1 = center + math.sin(rad) * 10
                    x2 = center + math.cos(rad) * length
                    y2 = center + math.sin(rad) * length
                    draw.line([x1, y1, x2, y2], fill='#FF4500', width=2)
                
                # Add some "debris" dots
                for _ in range(15):
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(radius * 0.5, radius * 1.2)
                    px = center + math.cos(angle) * dist
                    py = center + math.sin(angle) * dist
                    size = random.randint(2, 5)
                    color = random.choice(['#FF6B9D', '#FFB6C1', '#888888', '#FF4500'])
                    draw.ellipse([px - size, py - size, px + size, py + size], fill=color)
            
            # Flash effect
            if i == 0 or i == 1:
                draw.ellipse([center - 40, center - 40, center + 40, center + 40], 
                           fill='#FFFFFF')
            
            frames.append(img)
        return frames
    
    def create_dead_sprites(self):
        """Create dead/ghost sprite"""
        frames = []
        for i in range(4):
            img = Image.new('RGBA', (self.pet_size, self.pet_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            center = self.pet_size // 2
            float_offset = int(math.sin(i / 4 * math.pi * 2) * 3)
            
            # Ghost Stapler-y floating
            base_y = 50 + float_offset
            
            # Semi-transparent ghost Stapler-y body (bottom)
            draw.rectangle([center - 45, base_y + 20, center + 45, base_y + 35], 
                          fill='#E0E0FF88', outline='#B0B0FF', width=2)
            
            # Semi-transparent ghost Stapler-y top (slightly open)
            draw.rectangle([center - 40, base_y + 5, center + 40, base_y + 17], 
                          fill='#F0F0FF88', outline='#C0C0FF', width=2)
            
            # X_X eyes on ghost Stapler-y
            eye_y = base_y + 10
            draw.line([center - 15, eye_y - 2, center - 11, eye_y + 2], fill='#6495ED', width=2)
            draw.line([center - 15, eye_y + 2, center - 11, eye_y - 2], fill='#6495ED', width=2)
            draw.line([center + 11, eye_y - 2, center + 15, eye_y + 2], fill='#6495ED', width=2)
            draw.line([center + 11, eye_y + 2, center + 15, eye_y - 2], fill='#6495ED', width=2)
            
            # Halo above ghost Stapler-y
            halo_y = base_y - 10
            draw.ellipse([center - 25, halo_y, center + 25, halo_y + 8], 
                        outline='#FFD700', width=3)
            
            # Ghostly wisps
            wisp_y = base_y + 35
            wave = int(math.sin((i + 1) / 4 * math.pi * 2) * 5)
            draw.ellipse([center - 20 + wave, wisp_y, center - 10 + wave, wisp_y + 10], 
                        fill='#E0E0FF44', outline='#B0B0FF88', width=1)
            draw.ellipse([center + 10 - wave, wisp_y + 3, center + 20 - wave, wisp_y + 13], 
                        fill='#E0E0FF44', outline='#B0B0FF88', width=1)
            
            # RIP text
            if i % 2 == 0:
                draw.text([center - 10, base_y + 48], "RIP", fill='#888888')
            
            frames.append(img)
        return frames
    
    def draw_heart(self, draw, x, y, size, color):
        """Draw a heart shape"""
        # Two circles for top
        draw.ellipse([x, y, x + size, y + size], fill=color)
        draw.ellipse([x + size, y, x + size * 2, y + size], fill=color)
        # Triangle for bottom
        draw.polygon([
            (x, y + size // 2),
            (x + size, y + size * 2),
            (x + size * 2, y + size // 2)
        ], fill=color)
    
    def convert_sprites(self):
        """Convert PIL images to PhotoImages"""
        for state, images in self.sprite_images.items():
            self.sprites[state] = [ImageTk.PhotoImage(img) for img in images]
            flipped = [ImageOps.mirror(img) for img in images]
            self.sprites_flipped[state] = [ImageTk.PhotoImage(img) for img in flipped]
    
    def update_position(self):
        """Update window position"""
        try:
            self.root.geometry(f'+{int(self.x)}+{int(self.y)}')
        except:
            pass
    
    def animate(self):
        """Animation loop"""
        if not self.running:
            return
        
        # State-based animation config
        config = {
            "idle": 250,
            "walk": 100,
            "run": 80,
            "sleep": 600,
            "jump": 100,
            "fall": 150,
            "happy": 200,
            "eat": 250,
            "sit": 400,
            "explode": 100,
            "dead": 300,
            "thinking": 250,
        }
        
        delay = config.get(self.state, 200)
        
        # Get frames
        if self.direction == -1 and self.state in ["walk", "run", "jump", "fall"]:
            frames = self.sprites_flipped[self.state]
        else:
            frames = self.sprites[self.state]
        
        # Update frame
        if self.state == "explode":
            # Don't loop explosion
            if self.frame < len(frames) - 1:
                self.frame += 1
        else:
            self.frame = (self.frame + 1) % len(frames)
        
        # Draw
        self.canvas.delete("all")
        
        # Draw particles first (behind pet)
        if self.particles:
            self.draw_particles()
        
        # Draw pet sprite
        self.current_image = frames[self.frame]
        self.canvas.create_image(0, 0, anchor='nw', image=self.current_image)
        
        # Add respawn text when dead
        if self.is_dead and self.state == "dead":
            time_left = max(0, 5 - self.death_timer // 20)
            self.canvas.create_text(
                self.pet_size // 2, 
                self.pet_size - 10,
                text=f"Respawning in {time_left}...",
                fill='#888888',
                font=('Arial', 10)
            )
        
        self.root.after(delay, self.animate)
    
    def draw_particles(self):
        """Draw and update particles"""
        particles_to_remove = []
        
        for particle in self.particles:
            # Update particle physics
            particle['vy'] += 0.5  # Gravity
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vx'] *= 0.98  # Air resistance
            particle['life'] -= 1
            
            # Draw particle relative to canvas
            px = particle['x'] - self.x
            py = particle['y'] - self.y
            
            if 0 <= px <= self.pet_size and 0 <= py <= self.pet_size and particle['life'] > 0:
                size = particle['size']
                self.canvas.create_oval(
                    px - size, py - size,
                    px + size, py + size,
                    fill=particle['color'],
                    outline=''
                )
            
            if particle['life'] <= 0:
                particles_to_remove.append(particle)
        
        # Remove dead particles
        for particle in particles_to_remove:
            self.particles.remove(particle)
    
    def update_physics(self):
        """Physics update loop"""
        if not self.running:
            return
        
        # Use stored screen bounds (supports multi-monitor)
        screen_left = getattr(self, 'screen_left', 0)
        screen_top = getattr(self, 'screen_top', 0)
        screen_w = self.screen_width
        screen_h = self.screen_height
        
        # Don't apply physics if dead
        if self.is_dead:
            self.update_position()
            self.root.after(16, self.update_physics)
            return
        
        # Don't apply physics while being dragged
        if self.drag_data["dragging"]:
            self.velocity_x = 0
            self.velocity_y = 0
            self.root.after(16, self.update_physics)
            return
        
        # Apply gravity
        if not self.on_ground and self.state not in ["sleep", "sit"]:
            self.velocity_y += self.gravity
        
        # Apply friction
        self.velocity_x *= self.friction
        
        # Update position
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # Check impact speed for death
        impact_speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        death_threshold = 50.0  # Speed threshold for death - very high, requires extreme throws
        
        # Ground collision (respect virtual screen top)
        ground_y = screen_top + screen_h - self.pet_size - 40
        if self.y >= ground_y:
            if impact_speed > death_threshold:
                self.trigger_death()
            else:
                self.y = ground_y
                self.velocity_y = 0
                self.on_ground = True
                if self.state in ["jump", "fall"]:
                    self.state = "idle"
                    self.frame = 0
        else:
            self.on_ground = False
            if self.state not in ["jump", "sleep", "sit", "eat", "happy", "explode"] and self.velocity_y > 2:
                self.state = "fall"
        
        # Wall collision with death check (multi-monitor aware)
        left_bound = screen_left
        right_bound = screen_left + screen_w - self.pet_size
        if self.x < left_bound:
            if abs(self.velocity_x) > death_threshold:
                self.trigger_death()
            else:
                self.x = left_bound
                self.velocity_x = abs(self.velocity_x) * 0.5
                self.direction = 1
        elif self.x > right_bound:
            if abs(self.velocity_x) > death_threshold:
                self.trigger_death()
            else:
                self.x = right_bound
                self.velocity_x = -abs(self.velocity_x) * 0.5
                self.direction = -1
        
        # Ceiling collision with death check (respect virtual screen top)
        if self.y < screen_top:
            if abs(self.velocity_y) > death_threshold:
                self.trigger_death()
            else:
                self.y = 0
                self.velocity_y = abs(self.velocity_y) * 0.3
        
        self.update_position()
        self.root.after(16, self.update_physics)  # ~60 FPS
    
    def ai_loop(self):
        """AI behavior loop"""
        if not self.running:
            return
        
        # Handle death timer
        if self.is_dead:
            self.death_timer += 1
            # Respawn after 5 seconds (100 updates * 50ms)
            if self.death_timer > 100:
                self.respawn()
            self.root.after(50, self.ai_loop)
            return
        
        self.patrol_timer += 1
        
        # Don't do AI if being dragged or in special states
        if not self.drag_data["dragging"] and self.state not in ["jump", "happy", "eat", "thinking"]:
            
            # Random behavior changes
            if self.patrol_timer > 100 and random.random() < 0.02:
                self.patrol_timer = 0
                action = random.choices(
                    ["walk", "run", "idle", "sleep", "sit", "jump"],
                    weights=[25, 10, 30, 10, 15, 10]
                )[0]
                
                if action in ["walk", "run"]:
                    self.state = action
                    # Use stored screen bounds (multi-monitor aware)
                    left = getattr(self, 'screen_left', 0)
                    low = left + 50
                    high = left + max(100, self.screen_width - self.pet_size - 50)
                    if low >= high:
                        low = left
                        high = left + max(100, self.screen_width - self.pet_size)
                    self.target_x = random.randint(int(low), int(high))
                    self.frame = 0
                elif action == "jump":
                    if self.on_ground:
                        self.state = "jump"
                        self.velocity_y = -15
                        self.velocity_x = random.choice([-3, -2, 0, 2, 3])
                        self.frame = 0
                        self.root.after(600, lambda: self.return_to_state("idle"))
                elif action in ["idle", "sleep", "sit"]:
                    self.state = action
                    self.target_x = None
                    self.frame = 0
            
            # Move towards target
            if self.target_x is not None and self.state in ["walk", "run"]:
                dx = self.target_x - self.x
                
                if abs(dx) > 10:
                    self.direction = 1 if dx > 0 else -1
                    speed = 3.5 if self.state == "run" else 1.8
                    self.velocity_x = speed if dx > 0 else -speed
                else:
                    self.target_x = None
                    self.state = "idle"
                    self.velocity_x = 0
                    self.frame = 0
        
        self.root.after(50, self.ai_loop)
    
    def trigger_death(self):
        """Trigger death/explosion"""
        if self.is_dead:
            return
        
        self.is_dead = True
        self.state = "explode"
        self.frame = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.death_timer = 0
        
        # Create explosion particles
        center_x = self.x + self.pet_size // 2
        center_y = self.y + self.pet_size // 2
        
        for _ in range(30):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 15)
            self.particles.append({
                'x': center_x,
                'y': center_y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': random.randint(20, 40),
                'color': random.choice(['#FF6B9D', '#FFB6C1', '#FF4500', '#FFA500', '#888888']),
                'size': random.randint(2, 6)
            })
        
        # After explosion animation, show ghost
        self.root.after(800, self.become_ghost)
    
    def become_ghost(self):
        """Transition to ghost state after explosion"""
        if self.is_dead:
            self.state = "dead"
            self.frame = 0
    
    def respawn(self):
        """Respawn the pet"""
        self.is_dead = False
        self.state = "idle"
        self.frame = 0
        self.death_timer = 0
        self.particles.clear()
        
        # Respawn at center of PRIMARY monitor (not center of all monitors)
        self.x = self.primary_width // 2 - self.pet_size // 2
        self.y = self.primary_height // 2
        
        self.velocity_x = 0
        self.velocity_y = 0
        
        # Reset stats
        self.happiness = 80
        self.energy = 100
        self.hunger = 50
    
    def return_to_state(self, state):
        """Return to a specific state"""
        if self.state not in ["eat", "sleep", "thinking"]:  # Don't interrupt these
            self.state = state
            self.frame = 0
    
    def refresh_screen_bounds_periodically(self):
        """Refresh screen bounds every 30 seconds to handle monitor changes"""
        if not self.running:
            return
        
        self.update_screen_bounds()
        self.root.after(30000, self.refresh_screen_bounds_periodically)  # Every 30 seconds

    # --- History persistence helpers ---
    def history_file_path(self):
        base = os.path.dirname(__file__)
        return os.path.join(base, "brain", "history.json")

    def load_history(self):
        try:
            path = self.history_file_path()
            if not os.path.exists(path):
                return []
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                if not text:
                    return []
                return json.loads(text)
        except Exception as e:
            print(f"Failed to load history: {e}")
            return []

    def save_history(self):
        try:
            path = self.history_file_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(getattr(self, '_history', []), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def append_history(self, sender, message):
        from datetime import datetime
        entry = {
            'sender': sender,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        # Use the in-memory list directly; avoid re-reading from disk on every message.
        if not hasattr(self, '_history') or self._history is None:
            self._history = self.load_history()
        self._history.append(entry)
        self.save_history()
    
    def show_chat_dialog(self):
        """Show chat dialog for asking questions"""
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return
        
        # Create chat window
        self.chat_window = tk.Toplevel(self.root)
        self.chat_window.title("Chat with Stapler-y 📎")
        self.chat_window.geometry("400x500")
        self.chat_window.configure(bg='#F0F0F0')
        
        # Chat history display
        history_frame = tk.Frame(self.chat_window, bg='#F0F0F0')
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.chat_history = tk.Text(
            history_frame,
            wrap=tk.WORD,
            bg='#FFFFFF',
            font=('Arial', 10),
            state=tk.DISABLED,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.chat_history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Load persisted history and populate chat (do not re-save while populating)
        self._history = self.load_history()
        for entry in self._history:
            sender = entry.get('sender', 'You')
            message = entry.get('message', '')
            ts = entry.get('timestamp')
            color = '#2E7D32' if sender == 'You' else '#4A90E2'
            self.add_chat_message(sender, message, color=color, timestamp=ts, save=False)

        # Scrollbar
        scrollbar = tk.Scrollbar(history_frame, command=self.chat_history.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_history.config(yscrollcommand=scrollbar.set)
        
        # Input frame
        input_frame = tk.Frame(self.chat_window, bg='#F0F0F0')
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Question input
        self.question_entry = tk.Entry(
            input_frame,
            font=('Arial', 11),
            relief=tk.FLAT,
            bg='#FFFFFF'
        )
        self.question_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=5)
        self.question_entry.bind('<Return>', lambda e: self.ask_question())
        
        # Send button
        send_btn = tk.Button(
            input_frame,
            text="Ask",
            command=self.ask_question,
            bg='#4A90E2',
            fg='white',
            font=('Arial', 10, 'bold'),
            relief=tk.FLAT,
            padx=15,
            cursor='hand2'
        )
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Clear history button
        clear_btn = tk.Button(
            input_frame,
            text="Clear",
            command=self.clear_history_prompt,
            bg='#E53935',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            padx=10,
            cursor='hand2'
        )
        clear_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Focus on entry
        self.question_entry.focus()
    
    def add_chat_message(self, sender, message, color="#000000", timestamp=None, save=True):
        """Add a message to chat history and optionally persist it.

        Args:
            sender: display name (e.g., 'You' or 'Stapler-y')
            message: message text
            color: text color for sender tag
            timestamp: optional ISO timestamp string to display
            save: if True, append to persisted history file
        """
        if not hasattr(self, 'chat_history'):
            return

        from datetime import datetime
        if timestamp:
            # Try to format known ISO timestamps to HH:MM
            try:
                ts_dt = datetime.fromisoformat(timestamp)
                timestamp_display = ts_dt.strftime("%H:%M")
            except Exception:
                timestamp_display = str(timestamp)
        else:
            timestamp_display = datetime.now().strftime("%H:%M")

        self.chat_history.config(state=tk.NORMAL)

        # Sender name
        self.chat_history.insert(tk.END, f"\n{sender} ", f"sender_{sender}")
        self.chat_history.tag_config(f"sender_{sender}", foreground=color, font=('Arial', 10, 'bold'))

        # Timestamp
        self.chat_history.insert(tk.END, f"({timestamp_display})\n", "timestamp")
        self.chat_history.tag_config("timestamp", foreground="#888888", font=('Arial', 8))

        # Message
        self.chat_history.insert(tk.END, f"{message}\n", "message")
        self.chat_history.tag_config("message", font=('Arial', 10))

        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.see(tk.END)

        if save:
            self.append_history(sender, message)

    def clear_history_prompt(self):
        """Ask the user to confirm clearing history."""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear the chat history? This cannot be undone."):
            self.clear_history()

    def clear_history(self):
        """Clear in-memory and on-disk history and clear the chat display."""
        try:
            self._history = []
            self.save_history()
        except Exception as e:
            print(f"Failed to clear history: {e}")

        # Clear chat view if present
        if hasattr(self, 'chat_history'):
            try:
                self.chat_history.config(state=tk.NORMAL)
                self.chat_history.delete('1.0', tk.END)
                self.chat_history.config(state=tk.DISABLED)
            except Exception:
                pass

    # --- Screen viewing helpers ---
    def capture_screen(self):
        """Capture the virtual screen as a PIL Image. Returns None on failure."""
        try:
            left = getattr(self, 'screen_left', None)
            top = getattr(self, 'screen_top', None)
            w = getattr(self, 'screen_width', None)
            h = getattr(self, 'screen_height', None)

            # Prefer mss if available (robust multi-monitor capture)
            if mss:
                with mss.mss() as sct:
                    if None not in (left, top, w, h):
                        monitor = {
                            'left': int(left), 'top': int(top),
                            'width': int(w), 'height': int(h)
                        }
                    else:
                        # monitor 0 is the virtual screen in mss
                        monitor = sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    # Create PIL Image from raw data
                    img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
                    return img

            # Fallback to PIL ImageGrab if mss not available
            if ImageGrab:
                if None not in (left, top, w, h):
                    bbox = (int(left), int(top), int(left + w), int(top + h))
                    return ImageGrab.grab(bbox=bbox)
                else:
                    return ImageGrab.grab()
            return None
        except Exception as e:
            print(f"Failed to capture screen: {e}")
            return None

    def show_screen_view(self):
        """Open a simple window that shows the current screen capture."""
        img = self.capture_screen()
        if img is None:
            messagebox.showinfo("View Screen", "Screen capture not available on this system.")
            return

        # Create or reuse viewer window
        try:
            viewer = getattr(self, 'screen_viewer', None)
            if viewer and viewer.winfo_exists():
                viewer.lift()
                # update image
            else:
                viewer = tk.Toplevel(self.root)
                viewer.title("Screen View")
                self.screen_viewer = viewer

            # Resize image to fit window if necessary
            max_w, max_h = 800, 600
            img_w, img_h = img.size
            scale = min(1.0, max_w / img_w, max_h / img_h)
            if scale < 1.0:
                new_size = (int(img_w * scale), int(img_h * scale))
                # Use modern resampling attribute when available
                try:
                    resample = Image.Resampling.LANCZOS
                except Exception:
                    resample = getattr(Image, 'LANCZOS', Image.BICUBIC)
                img_disp = img.resize(new_size, resample)
            else:
                img_disp = img

            photo = ImageTk.PhotoImage(img_disp)
            # Keep reference to avoid GC
            self._screen_view_image = photo

            # Put image in label
            if hasattr(self, '_screen_view_label') and self._screen_view_label.winfo_exists():
                self._screen_view_label.config(image=photo)
            else:
                lbl = tk.Label(viewer, image=photo)
                lbl.pack(fill=tk.BOTH, expand=True)
                self._screen_view_label = lbl

            # Buttons frame
            btn_frame = getattr(self, '_screen_view_btns', None)
            if not btn_frame or not btn_frame.winfo_exists():
                btn_frame = tk.Frame(viewer)
                btn_frame.pack(fill=tk.X)
                refresh = tk.Button(btn_frame, text="Refresh", command=self.show_screen_view)
                refresh.pack(side=tk.LEFT, padx=4, pady=4)
                close = tk.Button(btn_frame, text="Close", command=viewer.destroy)
                close.pack(side=tk.RIGHT, padx=4, pady=4)
                self._screen_view_btns = btn_frame
        except Exception as e:
            print(f"Failed to open screen viewer: {e}")
    
    def ask_question(self):
        """Send question to AI"""
        if not hasattr(self, 'question_entry'):
            return
        
        question = self.question_entry.get().strip()
        if not question:
            return

        # Clear input
        self.question_entry.delete(0, tk.END)

        # Add user message to chat
        self.add_chat_message("You", question, "#2E7D32")

        # If the user entered a direct command (JSON or prefixed), execute locally
        raw = question.strip()
        is_direct_cmd = False
        if raw.startswith('{') and 'command' in raw:
            is_direct_cmd = True
        if raw.upper().startswith('COMMAND:') or raw.startswith('/') or raw.startswith('/cmd'):
            is_direct_cmd = True

        if is_direct_cmd:
            try:
                cmds = self.parse_ai_commands(question)
                if not cmds:
                    self.add_chat_message('System', 'No valid command found in input.', '#888888')
                    return
                for cmd in cmds:
                    result = self.handle_ai_command(cmd)
                    self.add_chat_message('System', result, '#888888')
            except Exception as e:
                self.add_chat_message('System', f'Error running command: {e}', '#888888')
            return

        # Otherwise, send to AI
        # Start thinking animation
        self.state = "thinking"
        self.is_thinking = True
        self.frame = 0

        # Call AI in background
        self.root.after(100, lambda: self.get_ai_response(question))
    
    def get_ai_response(self, question):
        """Kick off the AI call on a background thread so the UI stays responsive."""
        # Capture screen on the main thread before handing off
        try:
            screen_img = self.capture_screen()
        except Exception:
            screen_img = None

        def worker():
            try:
                answer = get_response(question, screen_image=screen_img)
            except Exception as e:
                answer = f"Oops, something went wrong 📎 ({e})"
            # Post results back to the main (tkinter) thread
            self.root.after(0, lambda: self._on_ai_response(answer))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ai_response(self, answer):
        """Called on the main thread once the AI has finished."""
        self.last_response = answer

        # Add AI response to chat
        self.add_chat_message("Stapler-y", answer, "#4A90E2")

        # Parse and handle any commands returned by the AI
        try:
            commands = self.parse_ai_commands(answer)
            for cmd in commands:
                result = self.handle_ai_command(cmd)
                if result:
                    self.add_chat_message("System", result, "#888888")
        except Exception as e:
            print(f"Error handling AI commands: {e}")

        # Return to happy state
        self.state = "happy"
        self.happiness = min(100, self.happiness + 5)
        self.root.after(2000, lambda: self.return_to_state("idle"))

        self.is_thinking = False
    
    def on_click(self, event):
        """Handle mouse click"""
        # Can't interact when dead
        if self.is_dead:
            return
        
        current_time = self.root.tk.call('clock', 'milliseconds')
        
        # Check for double-click (within 300ms)
        if current_time - self.last_click_time < 300:
            self.click_count += 1
            if self.click_count >= 2:
                # Double click - make happy!
                self.state = "happy"
                self.happiness = min(100, self.happiness + 20)
                self.frame = 0
                self.target_x = None
                self.root.after(1500, lambda: self.return_to_state("idle"))
                self.click_count = 0
        else:
            self.click_count = 1
        
        self.last_click_time = current_time
        
        # Start drag — store where inside the pet the user clicked (screen coords)
        # so we can keep that offset constant throughout the drag.
        self.drag_data["offset_x"] = event.x   # canvas-relative click position
        self.drag_data["offset_y"] = event.y
        self.drag_data["start_x"] = self.x
        self.drag_data["start_y"] = self.y
        self.drag_data["dragging"] = True
        # Seed velocity tracker so first on_drag has a valid baseline
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
        """Handle dragging — use screen-absolute coordinates so the pet
        stays pinned under the cursor regardless of window movement."""
        if not self.drag_data["dragging"]:
            return

        # Compute new window position: cursor screen pos minus the
        # canvas-relative offset recorded at click time.
        new_x = event.x_root - self.drag_data["offset_x"]
        new_y = event.y_root - self.drag_data["offset_y"]

        # Track instantaneous velocity (pixels/second) for throw-on-release
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
        """Handle mouse release — apply velocity measured during the drag."""
        if self.drag_data["dragging"]:
            # Use the instantaneous velocity tracked in on_drag (pixels/second).
            # Scale down to a reasonable per-frame unit (game runs ~60 fps).
            scale = 1.0 / 60.0
            self.velocity_x = self.drag_data["vel_x"] * scale
            self.velocity_y = self.drag_data["vel_y"] * scale

        self.drag_data["dragging"] = False
        self.happiness = min(100, self.happiness + 5)
    
    def on_mouse_enter(self, event):
        """Mouse enters pet area"""
        if not self.drag_data["dragging"] and self.state == "idle":
            # Small chance to react
            if random.random() < 0.3:
                self.state = "sit"
                self.frame = 0
    
    def on_mouse_leave(self, event):
        """Mouse leaves pet area"""
        pass
    
    def show_menu(self, event):
        """Show context menu"""
        menu = Menu(self.root, tearoff=0)
        
        if self.is_dead:
            # Special menu when dead
            menu.add_command(label="💀 Dead!", state="disabled")
            menu.add_command(label=f"⏱️  Respawn in {max(0, 5 - self.death_timer // 20)}s", state="disabled")
            menu.add_separator()
            menu.add_command(label="⚡ Revive Now", command=self.respawn)
            menu.add_separator()
            menu.add_command(label="❌ Quit", command=self.quit_app)
        else:
            # Normal menu
            menu.add_command(label="💬 Chat with Me!", command=self.show_chat_dialog)
            menu.add_separator()
            menu.add_command(label="🚶 Walk", command=self.cmd_walk)
            menu.add_command(label="🏃 Run", command=self.cmd_run)
            menu.add_command(label="🦘 Jump", command=self.cmd_jump)
            menu.add_command(label="🪑 Sit", command=self.cmd_sit)
            menu.add_command(label="🍪 Feed", command=self.cmd_feed)
            menu.add_command(label="❤️  Pet", command=self.cmd_pet)
            menu.add_separator()
            menu.add_command(label="😴 Sleep", command=self.cmd_sleep)
            menu.add_separator()
            menu.add_command(label=f"❤️  Happiness: {int(self.happiness)}%", state="disabled")
            menu.add_command(label=f"⚡ Energy: {int(self.energy)}%", state="disabled")
            menu.add_separator()
            menu.add_command(label=f"🖥️  Screen: {self.screen_width}x{self.screen_height}", state="disabled")
            menu.add_command(label="🔄 Refresh Monitors", command=self.update_screen_bounds)
            menu.add_command(label="👀 View Screen", command=self.show_screen_view)
            menu.add_separator()
            menu.add_command(label="💡 Throw EXTREMELY hard to explode!", state="disabled")
            menu.add_separator()
            menu.add_command(label="❌ Quit", command=self.quit_app)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def cmd_walk(self):
        """Menu: Walk"""
        self.state = "walk"
        self.frame = 0
        left = getattr(self, 'screen_left', 0)
        low = left + 50
        high = left + max(100, self.screen_width - self.pet_size - 50)
        if low >= high:
            low = left
            high = left + max(100, self.screen_width - self.pet_size)
        self.target_x = random.randint(int(low), int(high))
    
    def cmd_run(self):
        """Menu: Run"""
        self.state = "run"
        self.frame = 0
        left = getattr(self, 'screen_left', 0)
        low = left + 50
        high = left + max(100, self.screen_width - self.pet_size - 50)
        if low >= high:
            low = left
            high = left + max(100, self.screen_width - self.pet_size)
        self.target_x = random.randint(int(low), int(high))
    
    def cmd_jump(self):
        """Menu: Jump"""
        if self.on_ground:
            self.state = "jump"
            self.velocity_y = -18
            self.velocity_x = random.choice([-4, 0, 4])
            self.frame = 0
    
    def cmd_sit(self):
        """Menu: Sit"""
        self.state = "sit"
        self.frame = 0
        self.target_x = None
        self.velocity_x = 0
    
    def cmd_feed(self):
        """Menu: Feed"""
        self.state = "eat"
        self.frame = 0
        self.target_x = None
        self.velocity_x = 0
        self.hunger = max(0, self.hunger - 30)
        self.happiness = min(100, self.happiness + 15)
        self.energy = min(100, self.energy + 20)
        self.root.after(2000, lambda: self.return_to_state("idle"))
    
    def cmd_pet(self):
        """Menu: Pet (make happy)"""
        self.state = "happy"
        self.frame = 0
        self.target_x = None
        self.happiness = min(100, self.happiness + 25)
        self.root.after(2000, lambda: self.return_to_state("idle"))
    
    def cmd_sleep(self):
        """Menu: Sleep"""
        self.state = "sleep"
        self.frame = 0
        self.target_x = None
        self.velocity_x = 0
        self.energy = min(100, self.energy + 50)

    # --- AI command parsing and handling ---
    def parse_ai_commands(self, text: str) -> list:
        """Parse AI response text for commands.

        Supports:
        - JSON object containing {"command": "name", "args": {...}}
        - Lines starting with "COMMAND:" or "/cmd" or "/"
        Returns a list of command dicts: {"command": str, "args": dict}
        """
        cmds = []
        if not text:
            return cmds

        # Try to find a JSON object first
        try:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    if isinstance(obj, dict) and 'command' in obj:
                        cmds.append({'command': obj['command'], 'args': obj.get('args', {})})
                        return cmds
                except Exception:
                    pass
        except Exception:
            pass

        # Otherwise, parse line-based commands
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # COMMAND: action arg1=val arg2=val
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

    def handle_ai_command(self, cmd: dict) -> str:
        """Execute a single AI command dict and return a short result string."""
        name = cmd.get('command') or ''
        args = cmd.get('args') or {}
        name_l = name.lower()

        try:
            if name_l in ('walk', 'cmd_walk'):
                self.cmd_walk()
                return 'Started walking.'
            if name_l in ('run', 'cmd_run'):
                self.cmd_run()
                return 'Started running.'
            if name_l in ('jump', 'cmd_jump'):
                self.cmd_jump()
                return 'Jumped.'
            if name_l in ('sit', 'cmd_sit'):
                self.cmd_sit()
                return 'Sitting.'
            if name_l in ('eat', 'cmd_feed', 'feed'):
                self.cmd_feed()
                return 'Eating.'
            if name_l in ('pet', 'cmd_pet'):
                self.cmd_pet()
                return 'Petted.'
            if name_l in ('sleep', 'cmd_sleep'):
                self.cmd_sleep()
                return 'Sleeping.'
            if name_l in ('respawn',):
                self.respawn()
                return 'Respawned.'
            if name_l in ('quit', 'exit'):
                self.quit_app()
                return 'Quitting app.'
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
                    if x is not None:
                        self.x = float(x)
                    if y is not None:
                        self.y = float(y)
                    self.update_position()
                    return f'Moved to {self.x},{self.y}.'
                except Exception:
                    return 'Failed to move: invalid coordinates.'
            if name_l in ('clear_history', 'clear'):
                self.clear_history()
                return 'Cleared history.'
            if name_l in ('view_screen', 'show_screen'):
                self.show_screen_view()
                return 'Opened screen viewer.'
            if name_l in ('save_screenshot', 'screenshot'):
                img = self.capture_screen()
                if img:
                    import datetime
                    base = os.path.dirname(__file__)
                    path = os.path.join(base, 'brain', f'screenshot_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    img.save(path)
                    return f'Screenshot saved to {path}.'
                return 'Screenshot failed.'
            if name_l in ('say', 'speak', 'message'):
                text = args.get('text') or args.get('t') or ''
                if text:
                    self.add_chat_message('Stapler-y', text, '#4A90E2')
                    return 'Posted message.'

            return f'Unknown command: {name}.'
        except Exception as e:
            return f'Error executing command {name}: {e}'
    
    def quit_app(self):
        """Quit application"""
        self.running = False
        self.root.quit()
        try:
            self.root.destroy()
        except:
            pass
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit_app()
