from machine import Pin, ADC, PWM, I2C
import time
import dht
import _thread  
from battery import BatteryMonitor
from oled_ui import Display
from buzzer import AudioUI
from mpu6050 import MPU6050
from hcsr04 import Ultrasonic
from spider_core import SpiderCore
from spider_radio import SpiderRadio

#Hardware Initialization
tch1 = Pin(18, Pin.IN)
tch2 = Pin(19, Pin.IN)
t_sen = dht.DHT22(Pin(20))
li_ion = BatteryMonitor()
i2c_lock = _thread.allocate_lock() 
oled = Display()
beeper = AudioUI()
imu = MPU6050(oled.i2c) 
radar = Ultrasonic(trig_pin=16, echo_pin=17)
robot = SpiderCore(oled.i2c)
receiver = SpiderRadio()

_thread.start_new_thread(beeper.boot_up, ())
oled.boot_animation()

#GLOBAL STATE VARIABLES
ROBOT_MODE = "BENCH"  
last_robot_mode = "BENCH"
countdown_start_ms = 0
last_displayed_joy = "" 
last_radio_btn = 0
last_manual_update = 0
global_joy_x = 0
global_joy_y = 0
global_drive_mode = "ARCADE"

#CORE 1: THE PHYSICS ENGINE
def core1_physics_thread():
    global ROBOT_MODE
    last_loop_time = time.ticks_us()
    
    while True:
        current_time_us = time.ticks_us()
        dt = time.ticks_diff(current_time_us, last_loop_time) / 1000000.0
        last_loop_time = current_time_us
        if dt <= 0: dt = 0.001
        
        if ROBOT_MODE == "AUTO":
            i2c_lock.acquire()
            try:
                robot.tick(dt, imu, radar)
            finally:
                i2c_lock.release()
                
        elif ROBOT_MODE == "MANUAL":
            i2c_lock.acquire()
            try:
                robot.walk(speed=global_joy_y, turn=global_joy_x, delta_time=dt, imu_obj=imu, drive_mode=global_drive_mode)
            finally:
                i2c_lock.release()
            
        time.sleep_ms(4)

#CORE 0: THE EXECUTIVE BRAIN
current_screen = 0
total_screens = 4 
pet_animation_end = 0    
last_temp_read, last_screen_update = 0, 0
last_tch1, last_tch2 = 0, 0
tch2_start_time = 0
estop_start_time = 0       
temp = 0.0

robot.kill_motors()
_thread.start_new_thread(core1_physics_thread, ())

try:
    while True:
        curr_time = time.time()
        battery = li_ion.get_level()
        
        # 1. HARDWARE SAFETY (Overrides Everything)
        if battery <= 15 or battery == 100:
            if ROBOT_MODE != "BENCH":
                ROBOT_MODE = "BENCH"
                i2c_lock.acquire()
                robot.kill_motors() 
                i2c_lock.release()
            
            i2c_lock.acquire()
            oled.show_alert("LOW" if battery <= 15 else "FULL")
            i2c_lock.release()
            time.sleep(1) 
            continue

        if ROBOT_MODE != last_robot_mode:
            if ROBOT_MODE == "BENCH":
                i2c_lock.acquire()
                robot.kill_motors()
                i2c_lock.release()
                beeper.play_tone(500, 200) 
            last_robot_mode = ROBOT_MODE

        # 2. SENSOR & RADIO POLLING
        joy_x, joy_y, btn, is_connected = receiver.get_data()

        # 3. EMERGENCY STOP
        if ROBOT_MODE in ["AUTO", "MANUAL", "COUNTDOWN"]:
            curr_tch1 = tch1.value()
            curr_tch2 = tch2.value()
            
            if curr_tch1 == 1 or curr_tch2 == 1:
                if time.ticks_diff(time.ticks_ms(), estop_start_time) > 800:
                    ROBOT_MODE = "BENCH"
                    beeper.play_tone(400, 400)
            else:
                estop_start_time = time.ticks_ms()

        # 4. COUNTDOWN MODE
        if ROBOT_MODE == "COUNTDOWN":
            elapsed_ms = time.ticks_diff(time.ticks_ms(), countdown_start_ms)
            time_left = 5 - int(elapsed_ms / 1000)
            
            i2c_lock.acquire()
            oled.show_mode("AUTO", f"LAUNCH IN: {time_left}")
            i2c_lock.release()
            
            if time_left <= 0:
                beeper.play_tone(2000, 300) 
                
                i2c_lock.acquire()
                oled.show_mode("AUTO", "--- RUNNING ---") 
                i2c_lock.release()
                
                ROBOT_MODE = "AUTO" 

        # 5. MANUAL MODE (RADIO CONTROL)
        elif ROBOT_MODE == "MANUAL":
            #THE DEADMAN'S SWITCH
            if not is_connected:
                print("🚨 RADIO SIGNAL LOST! ABORTING 🚨")
                i2c_lock.acquire()
                oled.show_alert("RADIO LOST")
                robot.kill_motors()
                i2c_lock.release()
                beeper.play_tone(300, 500) 
                last_displayed_joy = "" 
                last_radio_btn = 0
                ROBOT_MODE = "BENCH" 
                continue

            #PROCESS LIVE TELEMETRY
            if btn == 1 and last_radio_btn == 0:
                beeper.click() 
                global_drive_mode = "TANK" if global_drive_mode == "ARCADE" else "ARCADE"    
            last_radio_btn = btn 
            
            #Feed the Bridge
            global_joy_x = joy_x
            global_joy_y = joy_y
            current_joy_str = f"X:{joy_x} Y:{joy_y}"
            mode_header = "ARCADE DRIVE" if global_drive_mode == "ARCADE" else "TANK SPIN"
            
            if current_joy_str != last_displayed_joy and time.ticks_diff(time.ticks_ms(), last_manual_update) > 100:
                i2c_lock.acquire()
                try:
                    oled.show_mode(mode_header, current_joy_str)
                finally:
                    i2c_lock.release()
                
                last_displayed_joy = current_joy_str
                last_manual_update = time.ticks_ms()

        # 6. BENCH MODE (Full UI)
        elif ROBOT_MODE == "BENCH":
            
            if curr_time - last_temp_read >= 2:
                try:
                    t_sen.measure()
                    temp = t_sen.temperature()
                except OSError: pass  
                last_temp_read = curr_time
                
            curr_tch1 = tch1.value()
            if curr_tch1 == 1 and last_tch1 == 0:
                current_screen = (current_screen + 1) % total_screens
                beeper.click()
                last_screen_update = 0 
            last_tch1 = curr_tch1

            curr_tch2 = tch2.value()
            if curr_tch2 == 1 and last_tch2 == 0:
                tch2_start_time = time.ticks_ms() 
            elif curr_tch2 == 0 and last_tch2 == 1:
                duration = time.ticks_diff(time.ticks_ms(), tch2_start_time)
                last_screen_update = 0 
                
                if duration >= 500: #LONG PRESS
                    beeper.play_tone(1500, 100) 
                    if current_screen == 2: 
                        ROBOT_MODE = "COUNTDOWN"
                        countdown_start_ms = time.ticks_ms() 
                    elif current_screen == 3: 
                        ROBOT_MODE = "MANUAL" 
                        
                        #Wipe memory before entering Manual mode
                        last_displayed_joy = "" 
                        last_radio_btn = 0
                        last_manual_update = time.ticks_ms() #Reset the manual stopwatch
                        
                        i2c_lock.acquire()
                        oled.show_mode("MANUAL", "WAITING FOR LINK")
                        i2c_lock.release()
                        
                elif duration > 50: #SHORT PRESS
                    beeper.click()
                    if current_screen == 0: pet_animation_end = curr_time + 2 
            last_tch2 = curr_tch2
            
            #OLED Drawing
            if curr_time - last_screen_update >= 1 or last_screen_update == 0:
                i2c_lock.acquire()
                try:
                    if current_screen == 0:   
                        dist = radar.get_distance_cm()
                        emo = "HAPPY" if curr_time < pet_animation_end else ("PANIC" if dist < 10 else "NORMAL")
                        oled.show_eyes(emo)
                    elif current_screen == 1:   
                        oled.show_hud(battery, temp)
                    elif current_screen == 2:
                        oled.show_mode("AUTO", "Hold Btn to Start")
                    elif current_screen == 3:
                        oled.show_mode("MANUAL", "Hold Btn to Start")
                finally:
                    i2c_lock.release()
                    
                if last_screen_update == 0: 
                    last_screen_update = curr_time
        
        time.sleep_ms(10)

except BaseException as e:
    if i2c_lock.locked(): i2c_lock.release()
    robot.kill_motors()
    print("EMERGENCY SHUTDOWN:", e)