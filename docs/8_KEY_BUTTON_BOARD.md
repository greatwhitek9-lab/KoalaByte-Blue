# KoalaByte Blue 8-Key Front Panel Button Board

Default front panel hardware is an 8 independent key module with header pins:

```text
VCC  GND  K1  K2  K3  K4  K5  K6  K7  K8
```

Use only Raspberry Pi 3.3V for VCC. Do not use 5V on this module when its K outputs connect to Raspberry Pi GPIO.

## Wiring

```text
Module VCC -> Pi 3.3V, physical pin 1 or 17
Module GND -> Pi GND, physical pin 39 or any Pi GND
K1 -> BCM5,  physical pin 29, Main Menu
K2 -> BCM6,  physical pin 31, Move Left / Back
K3 -> BCM13, physical pin 33, Enter / Select
K4 -> BCM19, physical pin 35, Move Right / Forward
K5 -> BCM26, physical pin 37, Up
K6 -> BCM21, physical pin 40, Down
K7 -> BCM20, physical pin 38, PWR control position
K8 -> BCM16, physical pin 36, Reset position
```

The software treats the keys as active-low inputs using Raspberry Pi internal pull-ups:

```text
idle / not pressed -> HIGH
pressed -> LOW
```

## PWR control note

A GPIO key can request a clean software halt while the Pi is already running. It cannot start a fully unpowered Raspberry Pi by software alone.

For true on/off from the same front-panel key, add a supported power-control board or latching power circuit between the battery bank and the Pi, or wire a separate approved wake/run circuit according to the Raspberry Pi model documentation.

## K7 and K8 placement

K7 and K8 stay on the far right of the 8-key board:

```text
K1 K2 K3 K4 K5 K6 K7 K8
menu left select right up down pwr reset
```
