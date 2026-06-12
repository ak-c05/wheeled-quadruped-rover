from machine import Pin, ADC
import time

class BatteryMonitor:
    def __init__(self, pin=26, multiplier=4.0303, cal=1.035):
        self.adc = ADC(Pin(pin))
        self.conversion_factor = (3.3 / 65535.0) * multiplier * cal
        self.display_v = 0.0

    def get_level(self):
        total = 0
        for _ in range(50):
            total += self.adc.read_u16()
            time.sleep_ms(2)   
        raw_avg = total / 50
        real_v = raw_avg * self.conversion_factor
        #Deadband filter
        if abs(real_v - self.display_v) > 0.05:
            self.display_v = real_v    
        #Calculate percentage based on 6.4V (0%) to 8.4V (100%)
        pct = ((self.display_v - 6.4) / 2.0) * 100
        return max(0, min(100, round(pct)))