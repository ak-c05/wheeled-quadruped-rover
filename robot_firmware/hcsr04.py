from machine import Pin, time_pulse_us
import time

class Ultrasonic:
    def __init__(self, trig_pin=16, echo_pin=17):
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)

    def get_distance_cm(self):
        # 1. Send a 10-microsecond sound pulse
        self.trig.value(0)
        time.sleep_us(5)
        self.trig.value(1)
        time.sleep_us(10)
        self.trig.value(0)
        try:
            # 2. Measure how long it takes for the echo to return
            # The 30000 timeout prevents the code from freezing if it misses the echo
            pulse_time = time_pulse_us(self.echo, 1, 30000)
            if pulse_time < 0:
                return 999 # Nothing detected in range
            # 3. Math: Speed of sound is 343 m/s
            distance = (pulse_time * 0.0343) / 2
            return round(distance, 1)
        except OSError:
            return 999