import time
import math

class MPU6050:
    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.address = address
        self.i2c.writeto_mem(self.address, 0x6B, bytearray([0x00]))
        time.sleep(0.1) 

    def _read_raw_data(self, register):
        high = self.i2c.readfrom_mem(self.address, register, 1)[0]
        low = self.i2c.readfrom_mem(self.address, register + 1, 1)[0]
        value = (high << 8) | low
        if value > 32768:
            value = value - 65536
        return value

    def get_accel(self):
        x = self._read_raw_data(0x3B)
        y = self._read_raw_data(0x3D)
        z = self._read_raw_data(0x3F)
        return {"x": x / 16384.0, "y": y / 16384.0, "z": z / 16384.0}

    def get_gyro(self):
        x = self._read_raw_data(0x43)
        y = self._read_raw_data(0x45)
        z = self._read_raw_data(0x47)
        return {"x": x / 131.0, "y": y / 131.0, "z": z / 131.0}

    def get_angles(self):
        """Calculates Pitch and Roll in degrees using the gravity vector"""
        accel = self.get_accel()
        x = accel['x']
        y = accel['y']
        z = accel['z']
        
        # Calculate angles and convert from radians to degrees
        pitch = math.degrees(math.atan2(x, math.sqrt(y*y + z*z)))
        roll = math.degrees(math.atan2(y, math.sqrt(x*x + z*z)))
        
        # Using round() to keep the numbers from flickering wildly
        return {"pitch": round(pitch, 1), "roll": round(roll, 1)}