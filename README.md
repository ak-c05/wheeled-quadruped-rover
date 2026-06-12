# Quadruped Active-Suspension Rover (Dual-Core RP2350)

A custom-engineered quadruped robotics platform featuring a dual-core Real-Time Operating System (RTOS), 2.4GHz custom telemetry, and an IMU-driven PID active suspension system. 

![Tank Spin Transformation](media/tank-spin_to_normal.gif)

*Demonstration of the on-the-fly kinematic transformation from Arcade Drive to zero-radius Tank Spin.*

---

## ⚙️ Core Architecture & Features

This project splits processing workloads across the Raspberry Pi Pico 2 W's dual cores to ensure zero latency between the user interface, RF communications, and the physical kinematics engine.

* **Dual-Core Processing (RTOS):** Core 0 handles the radio telemetry, OLED user interface, and environmental polling. Core 1 is strictly dedicated to running the real-time kinematics, motor PWM mapping, and physics engine.
* **Active PID Stabilization:** Integrated a custom Proportional-Integral-Derivative (PID) controller reading an MPU6050 6-axis IMU. The algorithm dynamically adjusts all 8 servo joints to keep the chassis perfectly level over uneven terrain.
* **Kinematic Transformation (4WS):** Engineered on-the-fly geometric offsets to switch the physical chassis between standard differential Arcade Steering and a true zero-radius concentric Tank Spin.
* **Custom 2.4GHz Telemetry & Failsafe:** Built a hardened radio pipeline using NRF24L01+ transceivers. Features edge-detection, variable transmission rates (preventing SPI buffer overflow), and a 1.5-second deadman's switch that automatically kills locomotion upon signal loss.

---

## 🛠️ Hardware Specifications

### The Robot (RP2350)
* **Microcontroller:** Raspberry Pi Pico 2 W
* **Locomotion:** 4x N20 DC Motors (Driven via L298N Module)
* **Suspension / Steering:** 4x SG90 Servos & 4x MG90 Servos (Driven via PCA9685 I2C Expander)
* **Sensors:** * MPU6050 (6-Axis IMU)
  * HC-SR04P (Ultrasonic / Collision Avoidance)
  * DHT22 (Environmental Monitoring)
* **Telemetry:** NRF24L01+ 2.4GHz Transceiver (Hardware filtered with parallel 100µF/0.1µF capacitors)
* **Power Distribution:** 2S LiPo Battery or 2x 18650 cells $\rightarrow$ 10A BMS $\rightarrow$ XL4015 Buck Converter (5V step-down for logic/servos). Custom 133kΩ voltage divider circuit for raw battery monitoring.

### The Bench Test Controller
* **Microcontroller:** Raspberry Pi Pico 
* **Display:** 2.8" TFT Display (ILI9341 SPI Controller)
* **Telemetry:** NRF24L01+ 2.4GHz Transceiver (Hardware filtered with parallel 100µF/0.1µF capacitors)
* **Inputs:** Analog 2-Axis Joystick with integrated push-button mode toggle
* **Power:** 1S 3.7V LiPo with TP4056 Charging/Protection Module

---

## 📂 Repository Structure

* `/robot_firmware` - Firmware flashed to the main Quadruped chassis (RP2350).
* `/controller_firmware` - Firmware flashed to the remote bench controller.
* `/hardware` - Detailed pinout schematics and power routing block diagrams.
* `/media` - Demonstration clips of the UI, autonomous capabilities, and active suspension.

---

## 🔌 Schematics & Wiring

Complete pinout mapping and the power routing block diagram can be found in the `/hardware` directory.
* [Power Routing Diagram](hardware/power_routing_diagram.jpeg)
* [Pinout & I2C/SPI Mappings](hardware/pinout_robo_&_controller.txt)

---

## 🎥 Full Video Demonstrations

For a complete look at the closed-loop system, including audio feedback and full-state machine execution:
* **[Manual Drive & Telemetry Link Test](media/manual-mode_robo.mp4)** - Showcasing zero-latency radio control, UI updates, and differential steering.
* **[Autonomous Evasion Protocol](media/auto-mode_robo.mp4)** - Demonstrating the ultrasonic detection, reverse, and pivot state machine.
