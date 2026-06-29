#!/usr/bin/env python3
"""KoalaByte Blue 8-key front-panel live test.

Button numbering is physical left-to-right across the 8-key module:

1 K1 Main Menu             -> BCM GPIO5  / physical pin 29
2 K2 Move Left / Back      -> BCM GPIO6  / physical pin 31
3 K3 Enter / Select        -> BCM GPIO13 / physical pin 33
4 K4 Move Right / Forward  -> BCM GPIO19 / physical pin 35
5 K5 Up                    -> BCM GPIO26 / physical pin 37
6 K6 Down                  -> BCM GPIO21 / physical pin 40
7 K7 PWR On/Off position   -> BCM GPIO20 / physical pin 38
8 K8 Reset                 -> BCM GPIO16 / physical pin 36
VCC                        -> Pi 3.3V only, physical pin 1 or 17
GND                        -> physical pin 39 or any Pi GND

Electrical behavior:

- Pi internal pull-up enabled in software with pull_up=True.
- Not pressed / idle reads HIGH.
- Pressed reads LOW.
"""

from __future__ import annotations

import signal
from gpiozero import Button

BUTTONS = {
    "k1_main_menu": {"number": 1, "pin": 5, "press": "main_menu"},
    "k2_left_back": {"number": 2, "pin": 6, "press": "move_left/back"},
    "k3_enter_select": {"number": 3, "pin": 13, "press": "select"},
    "k4_right_forward": {"number": 4, "pin": 19, "press": "move_right/forward"},
    "k5_up": {"number": 5, "pin": 26, "press": "up"},
    "k6_down": {"number": 6, "pin": 21, "press": "down"},
    "k7_pwr": {"number": 7, "pin": 20, "press": "pwr_toggle"},
    "k8_reset": {"number": 8, "pin": 16, "press": "reset"},
}

running = True


def stop(*_: object) -> None:
    global running
    running = False


def main() -> None:
    signal.signal(signal.SIGINT, stop)
    buttons = []
    print("KoalaByte Blue 8-key button-board test running. Press Ctrl+C to exit.")
    print("Electrical mode: VCC=3.3V only, internal pull-up enabled; not pressed=HIGH, pressed=LOW.")
    print("Press K1 through K8 left-to-right and confirm the printed command matches the wiring table.")
    print("Note: K7 is the PWR position. True power-on from a fully unpowered Pi requires power-control hardware.")
    for name, cfg in BUTTONS.items():
        number = int(cfg["number"])
        pin = int(cfg["pin"])
        press = str(cfg["press"])
        button = Button(pin, pull_up=True, bounce_time=0.05)
        button.when_pressed = lambda n=name, num=number, p=pin, cmd=press: print(
            f"button={num} name={n} pin_bcm={p} electrical=LOW event=press command={cmd}", flush=True
        )
        buttons.append(button)
    while running:
        signal.pause()
    for button in buttons:
        button.close()


if __name__ == "__main__":
    main()
