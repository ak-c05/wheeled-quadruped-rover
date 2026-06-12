from machine import Pin, PWM
import time

class AudioUI:
    def __init__(self, pin=6):
        self.speaker = PWM(Pin(pin))
        self.speaker.duty_u16(0)

    def play_tone(self, freq, duration_ms, volume=3000):
        """The core function that actually vibrates the hardware"""
        self.speaker.freq(freq)
        self.speaker.duty_u16(volume)   
        time.sleep_ms(duration_ms)     
        self.speaker.duty_u16(0)       

    def click(self):
        self.play_tone(2000, 30, volume=2000)

    def boot_up(self):
        self.play_tone(1000, 150)
        time.sleep_ms(50)
        self.play_tone(2000, 200)

    def low_battery(self):
        for _ in range(3):
            self.play_tone(400, 300, volume=5000)
            time.sleep_ms(150)
            
    def full_battery(self):
        self.play_tone(800, 100)
        self.play_tone(1200, 100)
        self.play_tone(1600, 150)