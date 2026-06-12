from machine import Pin, ADC, SPI
import time

try:
    from nrf24l01 import NRF24L01
    from ili9341 import Display, color565
except ImportError as e:
    print("MISSING LIBRARY:", e)
    raise

# 1. HARDWARE SETUP
#JOYSTICK
vrx = ADC(Pin(26))
vry = ADC(Pin(27))
sw = Pin(28, Pin.IN, Pin.PULL_UP) 

#SPI 0: NRF24L01 RADIO
spi0 = SPI(0, baudrate=4000000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
nrf_csn = Pin(17, Pin.OUT, value=1)
nrf_ce = Pin(20, Pin.OUT, value=0)

nrf = NRF24L01(spi0, nrf_csn, nrf_ce, payload_size=32)
nrf.set_channel(115)
nrf.open_tx_pipe(b'ROBOT')

#SPI 1: ILI9341 TFT SCREEN
spi1 = SPI(1, baudrate=40000000, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
tft_cs = Pin(9, Pin.OUT)
tft_dc = Pin(8, Pin.OUT)
tft_rst = Pin(13, Pin.OUT)

display = Display(spi1, dc=tft_dc, cs=tft_cs, rst=tft_rst, width=240, height=320, rotation=270)

# 2. COLOR PALETTE & KINEMATICS
RED = color565(0, 0, 255)
GREEN = color565(0, 255, 0)
BLUE = color565(255, 200, 0)
WHITE = color565(255, 255, 255)
BLACK = color565(0, 0, 0)
GRAY = color565(100, 100, 100)

def map_joystick(val, center, deadband, min_val, max_val=65535):
    """
    Advanced Linear Interpolation with dynamic minimum thresholds.
    """
    if (center - deadband) <= val <= (center + deadband): 
        return 0
    elif val > (center + deadband):
        # Forward/Right movement mapping
        return min(100, int((val - (center + deadband)) / (max_val - (center + deadband)) * 100))
    else:
        # Reverse/Left movement mapping
        return max(-100, int((val - (center - deadband)) / ((center - deadband) - min_val) * 100))

# 3. DRAW THE STATIC GUI
display.clear(BLACK)

display.draw_rectangle(0, 0, 240, 25, BLUE)
display.draw_text8x8(40, 8, "TRANSMITTER ACTIVE", WHITE)

display.draw_rectangle(10, 40, 220, 120, GRAY)
display.draw_text8x8(20, 50, "LIVE TELEMETRY", BLUE)

display.draw_text8x8(20, 80, "X-Axis:", WHITE)
display.draw_text8x8(20, 100, "Y-Axis:", WHITE)
display.draw_text8x8(20, 120, "Button:", WHITE)
display.draw_text8x8(20, 140, "Radio :", WHITE)

display.draw_rectangle(0, 295, 240, 25, BLUE)
display.draw_text8x8(30, 303, "Link Established.", WHITE)

# 4. MAIN LOOP
last_x, last_y, last_btn, last_status = -999, -999, -1, ""

try:
    while True:
        #1. Read Raw Hardware
        raw_x = vrx.read_u16()
        raw_y = vry.read_u16()
        
        #2. Map constraints using your exact, updated photographic data
        #X Axis: Center 33900. Deadband +/- 1000. Minimum ~2100.
        clean_x = map_joystick(raw_x, center=33900, deadband=1000, min_val=2100)
        
        #Y Axis: Center 34550. Deadband +/- 1000. Minimum ~2200.
        clean_y = map_joystick(raw_y, center=34550, deadband=1000, min_val=2200)
        
        #PULL_UP means a physical press grounds the pin to 0. 
        btn = 1 if sw.value() == 0 else 0
        
        #3. Transmit Radio Data (Dynamic string length safely handled by 32-byte payload)
        payload = f"X:{clean_x},Y:{clean_y},B:{btn}"
        radio_status = "OK   "
        status_color = GREEN
        
        try:
            nrf.send(payload.encode('utf-8'))
        except OSError:
            radio_status = "FAIL " 
            status_color = RED

        #4. Smart UI Updates
        if clean_x != last_x:
            display.fill_rectangle(90, 80, 50, 10, BLACK)
            display.draw_text8x8(90, 80, str(clean_x), WHITE)
            last_x = clean_x
            
        if clean_y != last_y:
            display.fill_rectangle(90, 100, 50, 10, BLACK)
            display.draw_text8x8(90, 100, str(clean_y), WHITE)
            last_y = clean_y
            
        if btn != last_btn:
            display.fill_rectangle(90, 120, 80, 10, BLACK)
            display.draw_text8x8(90, 120, "PRESSED" if btn else "RELEASED", WHITE)
            last_btn = btn
            
        if radio_status != last_status:
            display.fill_rectangle(90, 140, 50, 10, BLACK)
            display.draw_text8x8(90, 140, radio_status, status_color)
            last_status = radio_status
        
        time.sleep_ms(50)

except KeyboardInterrupt:
    print("Transmitter Shutdown.")