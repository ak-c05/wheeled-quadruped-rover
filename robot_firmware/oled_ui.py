from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time
import random
import math

class Display:
    def __init__(self, scl_pin=5, sda_pin=4):
        self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.screen = SSD1306_I2C(128, 64, self.i2c)

    def clear(self):
        self.screen.fill(0)

    def _draw_circle(self, x0, y0, r, color):
        f = 1 - r
        ddF_x = 1
        ddF_y = -2 * r
        x = 0
        y = r
        self.screen.vline(x0, y0 - r, 2 * r + 1, color)
        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y
            x += 1
            ddF_x += 2
            f += ddF_x
            self.screen.vline(x0 + x, y0 - y, 2 * y + 1, color)
            self.screen.vline(x0 - x, y0 - y, 2 * y + 1, color)
            self.screen.vline(x0 + y, y0 - x, 2 * x + 1, color)
            self.screen.vline(x0 - y, y0 - x, 2 * x + 1, color)

    def _fill_round_rect(self, x, y, w, h, r, color):
        """Draws a solid rectangle with perfectly curved corners"""
        # Draw the intersecting central cross
        self.screen.fill_rect(x + r, y, w - 2 * r, h, color)
        self.screen.fill_rect(x, y + r, w, h - 2 * r, color)
        
        self._draw_circle(x + r, y + r, r, color)                   # Top Left
        self._draw_circle(x + w - r - 1, y + r, r, color)           # Top Right
        self._draw_circle(x + r, y + h - r - 1, r, color)           # Bottom Left
        self._draw_circle(x + w - r - 1, y + h - r - 1, r, color)   # Bottom Right

    def show_hud(self, battery_level, temp_value):
        self.clear()
        self.screen.rect(0, 0, 128, 5, 1)
        self.screen.rect(0, 59, 128, 5, 1)
        self.screen.text("--- MAIN HUD ---", 0, 10)
        self.screen.text(f"Battery: {battery_level}%", 0, 25)
        self.screen.text(f"Temp: {temp_value:2.1f} C", 0, 35)
        self.screen.rect(82, 35, 3, 3, 1)
        self.screen.show()
    
    def show_alert(self, alert_type):
        self.clear()
        self.screen.rect(0, 0, 128, 64, 1) 
        self.screen.rect(2, 2, 124, 60, 1) 
        
        if alert_type == "LOW":
            self.screen.text("!!! WARNING !!!", 4, 15)
            self.screen.text("LOW BATTERY", 20, 35)
            self.screen.text("CHARGE NOW", 25, 45)
        elif alert_type == "FULL":
            self.screen.text("*** STATUS ***", 8, 15)
            self.screen.text("BATTERY FULL", 16, 35)
            self.screen.text("100%", 48, 45)
            
        self.screen.show()
        
    def boot_animation(self):
        self.clear()
        self.screen.text("OS BOOTING...", 16, 15)
        self.screen.rect(14, 35, 100, 10, 1)
        for i in range(100):
            fill_width = int((i / 100) * 96)
            self.screen.fill_rect(16, 37, fill_width, 6, 1)
            self.screen.show()
            time.sleep(0.0001) 
        time.sleep(0.3)
        
    def show_kinematics(self, pitch, roll):
        self.clear()
        self.screen.text("   KINEMATICS", 0, 0)
        self.screen.rect(0, 2, 20, 5, 1)
        self.screen.rect(108, 2, 20, 5, 1)
        self.screen.text(f"Pitch: {pitch:>5} deg", 0, 25)
        self.screen.text(f"Roll:  {roll:>5} deg", 0, 40)
        self.screen.show()
        
    def show_menu(self, selected_index):
        self.clear()
        self.screen.text("--- MAIN MENU ---", 0, 0)
        options = ["Kinematics"]
        y_pos = 15
        for index, text in enumerate(options):
            if index == selected_index:
                self.screen.text(f"> {text}", 0, y_pos)
            else:
                self.screen.text(f"  {text}", 0, y_pos)
            y_pos += 15
        self.screen.show()
        
    def show_eyes(self, emotion="NORMAL"):
        self.clear()
        
        offset_x, offset_y = 0, 0
        if emotion == "PANIC":
            offset_x = random.choice([-3, -1, 0, 1, 3])
            offset_y = random.choice([-2, 0, 2])

        if emotion == "HAPPY":
            # Thick, smooth arches ^ ^
            self._fill_round_rect(24, 20, 28, 16, 8, 1) # Left
            self._fill_round_rect(76, 20, 28, 16, 8, 1) # Right
            self._fill_round_rect(24, 26, 28, 16, 8, 0)
            self._fill_round_rect(76, 26, 28, 16, 8, 0)
            
            # SMILE
            self._draw_circle(64, 42, 6, 1)           # Draw a small white circle
            self.screen.fill_rect(56, 32, 16, 10, 0)  # Erase the top half with a black box

        elif emotion == "PANIC":
            # Eyes pulled slightly down so they aren't hitting the top of the screen
            self._fill_round_rect(20 + offset_x, 14 + offset_y, 32, 32, 12, 1) 
            self._fill_round_rect(24 + offset_x, 18 + offset_y, 24, 24, 8, 0) 
            self._fill_round_rect(32 + offset_x, 26 + offset_y, 8, 8, 3, 1)   
            
            self._fill_round_rect(76 + offset_x, 14 + offset_y, 32, 32, 12, 1) 
            self._fill_round_rect(86 + offset_x, 24 + offset_y, 12, 12, 5, 0) 
            
            # SINE WAVE MOUTH
            for x in range(52, 76):
                # Y moved from 56 up to 50
                y = 50 + int(math.sin(x * 0.6) * 3) 
                self.screen.fill_rect(x + offset_x, y + offset_y, 2, 2, 1)

        else: # NORMAL
            is_blinking = random.random() < 0.05 
            
            if is_blinking:
                self._fill_round_rect(24, 24, 28, 6, 3, 1) 
                self._fill_round_rect(76, 24, 28, 6, 3, 1) 
            else:
                self._fill_round_rect(24, 16, 28, 28, 10, 1) 
                self._fill_round_rect(76, 16, 28, 28, 10, 1) 
            
            # STRAIGHT MOUTH
            # Y moved from 55 up to 48
            self._fill_round_rect(52, 48, 24, 4, 1, 1) 

        self.screen.show()
        
    def show_mode(self, mode_name, status_msg="Hold Btn to Start"):
        self.clear()
        self.screen.rect(0, 0, 128, 15, 1)
        self.screen.text(f" {mode_name} MODE ", 15, 4)
        
        # Center the status message roughly
        self.screen.text(status_msg, 0, 35)
        self.screen.show()