from machine import Pin, PWM
import time
import math

class SpiderCore:
    def __init__(self, i2c_bus):
        #I2C & PCA9685 INITIALIZATION
        self.i2c = i2c_bus
        self.PCA_ADDR = 0x40
        self._pca_init()
        
        #L298N MOTOR PINS
        self.ENA = PWM(Pin(14)); self.ENA.freq(1000); self.ENA.duty_u16(0)
        self.ENB = PWM(Pin(15)); self.ENB.freq(1000); self.ENB.duty_u16(0)
        self.IN1 = Pin(10, Pin.OUT); self.IN2 = Pin(11, Pin.OUT)
        self.IN3 = Pin(12, Pin.OUT); self.IN4 = Pin(13, Pin.OUT)

        #TUNING VARIABLES
        self.Kp_pitch = 1.5;  self.Ki_pitch = 0.02; self.Kd_pitch = 0.1
        self.Kp_roll  = 1.0;  self.Ki_roll  = 0.01; self.Kd_roll  = 0.05
        
        self.MAX_PWM = int((70 / 100.0) * 65535) 
        self.TURN_PWM = int((85 / 100.0) * 65535) # High-torque pivot
        self.RAMP_STEP = 1500 

        #KINEMATICS
        self.TRIM = {0: 80, 1: 80, 2: 80, 3: 90, 8: 130, 9: 30, 12: 120, 15: 40}
        self.current_angles = {
            0: -999, 1: -999, 2: -999, 3: -999, 
            8: -999, 9: -999, 12: -999, 15: -999
        }
        self.LIMITS = {
            0: (0, 180), 1: (0, 180), 2: (0, 180), 3: (0, 180),
            8: (0, 180), 9: (0, 180), 12: (10, 170), 15: (0, 155)
        }
        self.MAX_BEND = 40
        
        #STATE TRACKERS
        self.STATE = "DRIVING"
        self.EVADE_PHASE = 0
        self.evade_time = 0
        self.last_ping_time = time.ticks_ms()
        self.current_pwm = 0
        self.target_pwm = 0
        
        #PID MEMORY
        self.pitch_filtered = 0.0; self.roll_filtered = 0.0
        self.i_pitch = 0.0; self.last_err_pitch = 0.0
        self.i_roll = 0.0;  self.last_err_roll = 0.0
        
        #Calibrate Gyro on boot
        print("Calibrating Spider Gyros...")
        self.gx_off, self.gy_off = 0.0, 0.0

    def _pca_init(self):
        self.i2c.writeto_mem(self.PCA_ADDR, 0x00, b'\x10')
        prescale = int((25000000.0 / 4096 / 50) - 0.5)
        self.i2c.writeto_mem(self.PCA_ADDR, 0xFE, bytes([prescale]))
        self.i2c.writeto_mem(self.PCA_ADDR, 0x00, b'\x20')
        time.sleep_ms(5)

    def set_servo(self, channel, requested_angle):
        min_angle, max_angle = self.LIMITS.get(channel, (0, 180))
        safe_angle = max(min_angle, min(max_angle, requested_angle)) 
        
        #THE DEADBAND FILTER
        if abs(safe_angle - self.current_angles[channel]) < 1.5:
            return
            
        self.current_angles[channel] = safe_angle
        
        pulse_length = int(122 + (safe_angle / 180.0) * 369)
        reg = 0x06 + (channel * 4)
        try:
            self.i2c.writeto_mem(self.PCA_ADDR, reg, bytes([0, 0, pulse_length & 0xFF, pulse_length >> 8]))
        except OSError: pass

    #Motor Directions
    def dir_fwd(self): self.IN1.high(); self.IN2.low(); self.IN3.high(); self.IN4.low()
    def dir_bwd(self): self.IN1.low(); self.IN2.high(); self.IN3.low(); self.IN4.high()
    def dir_piv(self): self.IN1.low(); self.IN2.high(); self.IN3.high(); self.IN4.low()
    def dir_brk(self): self.IN1.low(); self.IN2.low(); self.IN3.low(); self.IN4.low()

    def kill_motors(self):
        self.dir_brk()
        self.ENA.duty_u16(0); self.ENB.duty_u16(0)
        for channel, base_angle in self.TRIM.items():
            self.set_servo(channel, base_angle)

    def update_suspension(self, dt, imu_obj, turn_offset=0, drive_mode="ARCADE"):
        """ Reusable PID Active Suspension Core with 4-Wheel Steering """
        try:
            acc = imu_obj.get_accel()
            gyr = imu_obj.get_gyro()
            
            acc_x = acc['y']; acc_y = acc['x']; acc_z = acc['z']
            gyro_x = gyr['y']; gyro_y = gyr['x']

            pitch_accel = math.atan2(acc_y, math.sqrt(acc_x**2 + acc_z**2)) * 57.2958
            roll_accel = math.atan2(-acc_x, acc_z) * 57.2958

            self.pitch_filtered = 0.98 * (self.pitch_filtered + gyro_y * dt) + 0.02 * pitch_accel
            self.roll_filtered = 0.98 * (self.roll_filtered + gyro_x * dt) + 0.02 * roll_accel

            err_p = 0.0 - self.pitch_filtered
            err_r = 0.0 - self.roll_filtered

            self.i_pitch = max(-20, min(20, self.i_pitch + err_p * dt))
            d_pitch = (err_p - self.last_err_pitch) / dt
            self.last_err_pitch = err_p
            pid_pitch = (self.Kp_pitch * err_p) + (self.Ki_pitch * self.i_pitch) + (self.Kd_pitch * d_pitch)

            self.i_roll = max(-20, min(20, self.i_roll + err_r * dt))
            d_roll = (err_r - self.last_err_roll) / dt
            self.last_err_roll = err_r
            pid_roll = (self.Kp_roll * err_r) + (self.Ki_roll * self.i_roll) + (self.Kd_roll * d_roll)

            #RELATIVE ACTIVE 4-WHEEL STEERING (HIPS)
            if drive_mode == "ARCADE":
                steer_angle = (turn_offset / 100.0) * 35 
                
                self.set_servo(3, int(self.TRIM[3] + steer_angle)) # Front Left
                self.set_servo(2, int(self.TRIM[2] + steer_angle)) # Front Right
                self.set_servo(1, int(self.TRIM[1] - steer_angle)) # Back Left
                self.set_servo(0, int(self.TRIM[0] - steer_angle)) # Back Right
                
            elif drive_mode == "TANK":
                self.set_servo(3, int(self.TRIM[3] + 45)) # Front Left Offset
                self.set_servo(2, int(self.TRIM[2] - 45)) # Front Right Offset
                self.set_servo(1, int(self.TRIM[1] - 45)) # Back Left Offset
                self.set_servo(0, int(self.TRIM[0] + 45)) # Back Right Offset

            #PID ACTIVE SUSPENSION (KNEES)
            bend_FL = max(-self.MAX_BEND, min(self.MAX_BEND, -pid_pitch + pid_roll))
            bend_FR = max(-self.MAX_BEND, min(self.MAX_BEND, pid_pitch + pid_roll))
            bend_BL = max(-self.MAX_BEND, min(self.MAX_BEND, -pid_pitch + pid_roll))
            bend_BR = max(-self.MAX_BEND, min(self.MAX_BEND, pid_pitch + pid_roll))

            self.set_servo(12, int(self.TRIM[12] + bend_FL)) 
            self.set_servo(15, int(self.TRIM[15] + bend_FR)) 
            self.set_servo(9,  int(self.TRIM[9]  + bend_BL))   
            self.set_servo(8,  int(self.TRIM[8]  + bend_BR))   
        except OSError:
            pass

    def tick(self, dt, imu_obj, radar_obj):
        """ The Main Brain Function. Call this every loop in main.py """
        current_ms = time.ticks_ms()
        
        #1. NAVIGATION & VISION
        dist = 999
        if time.ticks_diff(current_ms, self.last_ping_time) > 50:
            dist = radar_obj.get_distance_cm()
            self.last_ping_time = current_ms

        if self.STATE == "DRIVING":
            self.dir_fwd()
            self.target_pwm = self.MAX_PWM
            if dist < 40:
                self.STATE = "EVADING"; self.EVADE_PHASE = 1; self.evade_time = current_ms

        elif self.STATE == "EVADING":
            if self.EVADE_PHASE == 1: 
                self.target_pwm = 0 
                if self.current_pwm == 0: 
                    self.EVADE_PHASE = 2; self.dir_bwd(); self.evade_time = current_ms
            elif self.EVADE_PHASE == 2: 
                self.target_pwm = self.MAX_PWM
                if time.ticks_diff(current_ms, self.evade_time) > 500: 
                    self.EVADE_PHASE = 3; self.target_pwm = 0
            elif self.EVADE_PHASE == 3: 
                if self.current_pwm == 0: 
                    self.EVADE_PHASE = 4; self.dir_piv(); self.target_pwm = self.TURN_PWM; self.evade_time = current_ms
            elif self.EVADE_PHASE == 4: 
                if time.ticks_diff(current_ms, self.evade_time) > 1200: 
                    self.EVADE_PHASE = 5; self.target_pwm = 0
            elif self.EVADE_PHASE == 5: 
                if self.current_pwm == 0: 
                    fresh_dist = radar_obj.get_distance_cm()
                    time.sleep_ms(50) 
                    fresh_dist_2 = radar_obj.get_distance_cm()
                    if fresh_dist > 40 and fresh_dist_2 > 40: 
                        self.STATE = "DRIVING"
                    else:
                        self.EVADE_PHASE = 4; self.dir_piv(); self.target_pwm = self.TURN_PWM; self.evade_time = current_ms

        #2. MOTOR SLEW RATE
        if self.current_pwm < self.target_pwm: self.current_pwm = min(self.target_pwm, self.current_pwm + self.RAMP_STEP)
        elif self.current_pwm > self.target_pwm: self.current_pwm = max(self.target_pwm, self.current_pwm - self.RAMP_STEP)
        self.ENA.duty_u16(self.current_pwm); self.ENB.duty_u16(self.current_pwm)

        #3. ACTIVE SUSPENSION
        if self.STATE == "DRIVING":
            self.update_suspension(dt, imu_obj) 
        else:
            for channel, base_angle in self.TRIM.items():
                self.set_servo(channel, base_angle)
            self.i_pitch, self.last_err_pitch = 0.0, 0.0
            self.i_roll, self.last_err_roll = 0.0, 0.0
            
    def stand_idle(self):
        """ Halts the robot and resets memory to prevent violent jerks """
        self.kill_motors()
        self.i_pitch = 0.0
        self.i_roll = 0.0
        self.last_err_pitch = 0.0
        self.last_err_roll = 0.0

    def walk(self, speed, turn, delta_time, imu_obj, drive_mode="ARCADE"):
        """ Arcade Drive & Tank Transformation """
        
        #1. MOTOR MATH INTERCEPT
        if drive_mode == "ARCADE":
            left_power = speed + turn
            right_power = speed - turn
        elif drive_mode == "TANK":
            left_power = turn * 0.5
            right_power = -turn * 0.5

        max_power = max(abs(left_power), abs(right_power))
        if max_power > 100:
            left_power = (left_power / max_power) * 100
            right_power = (right_power / max_power) * 100

        #2. DRIVE LEFT MOTOR (IN1 & IN2)
        if left_power > 0:
            self.IN1.high(); self.IN2.low()
        elif left_power < 0:
            self.IN1.low(); self.IN2.high()
        else:
            self.IN1.low(); self.IN2.low() # Brake

        #3. DRIVE RIGHT MOTOR (IN3 & IN4)
        if right_power > 0:
            self.IN3.high(); self.IN4.low()
        elif right_power < 0:
            self.IN3.low(); self.IN4.high()
        else:
            self.IN3.low(); self.IN4.low() # Brake

        #4. APPLY PWM (Power Delivery)
        left_pwm = int((abs(left_power) / 100.0) * self.MAX_PWM)
        right_pwm = int((abs(right_power) / 100.0) * self.MAX_PWM)

        self.ENA.duty_u16(left_pwm)
        self.ENB.duty_u16(right_pwm)

        #5. ENGAGE ACTIVE SUSPENSION & 4-WHEEL STEERING
        self.update_suspension(delta_time, imu_obj, turn_offset=turn, drive_mode=drive_mode)