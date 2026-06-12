from machine import Pin, SPI
from nrf24l01 import NRF24L01
import time

class SpiderRadio:
    def __init__(self, sck_pin=2, mosi_pin=3, miso_pin=0, csn_pin=1, ce_pin=8, channel=115):
        self.spi = SPI(0, baudrate=4000000, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))
        self.csn = Pin(csn_pin, Pin.OUT, value=1)
        self.ce = Pin(ce_pin, Pin.OUT, value=0)
        
        self.nrf = NRF24L01(self.spi, self.csn, self.ce, payload_size=32)
        self.nrf.set_channel(channel)
        self.nrf.open_rx_pipe(1, b'ROBOT')
        self.nrf.start_listening()
        
        self.last_packet_time = time.ticks_ms()
        self.FAILSAFE_TIMEOUT_MS = 1500

        self.last_x = 0
        self.last_y = 0
        self.last_b = 0
        
    def _parse_payload(self, payload_str):
        try:
            clean_str = payload_str.replace('\x00', '').strip()
            if not clean_str: return None, None, None
        
            parts = clean_str.split(',')
            if len(parts) != 3: return None, None, None
        
            x = int(parts[0].split(':')[1])
            y = int(parts[1].split(':')[1])
            b = int(parts[2].split(':')[1])
            return x, y, b
        except:
            return None, None, None

    def get_data(self):
        #Check for new data
        if self.nrf.any():
            while self.nrf.any():
                raw_bytes = self.nrf.recv()
            payload = raw_bytes.decode('utf-8', 'ignore')
            x, y, b = self._parse_payload(payload)
            
            #If the packet was clean, update our memory!
            if x is not None:
                self.last_x = x
                self.last_y = y
                self.last_b = b
                self.last_packet_time = time.ticks_ms()
                
        #Check Failsafe
        time_since_last = time.ticks_diff(time.ticks_ms(), self.last_packet_time)
        is_connected = True
        
        if time_since_last > self.FAILSAFE_TIMEOUT_MS:
            is_connected = False
            self.last_x, self.last_y, self.last_b = 0, 0, 0 
            
        #ALWAYS return a real number, never 'None'
        return self.last_x, self.last_y, self.last_b, is_connected