#!/usr/bin/env python3
"""KoalaByte Blue RevA6 six-button front-panel test.

Button numbering is physical left-to-right across the front panel:

1 Main Menu             -> BCM GPIO5  / physical pin 29
2 Move Left / Back      -> BCM GPIO6  / physical pin 31
3 Enter / Select        -> BCM GPIO13 / physical pin 33, hold 3s for shutdown event
4 Move Right / Forward  -> BCM GPIO19 / physical pin 35
5 Up                    -> BCM GPIO26 / physical pin 37
6 Down                  -> BCM GPIO21 / physical pin 40
GND                     -> physical pin 39 or any Pi GND
"""

from __future__ import annotations

import signal
from gpiozero import Button

BUTTONS = {
    "button_1_main_menu": {"number": 1, "pin": 5, "press": "main_menu"},
    "button_2_left_back": {"number": 2, "pin": 6, "press": "move_left/back"},
    "button_3_enter_select": {"number": 3, "pin": 13, "press": "select", "hold": "shutdown"},
    "button_4_right_forward": {"number": 4, "pin": 19, "press": "move_right/forward"},
    "button_5_up": {"number": 5, "pin": 26, "press": "up"},
    "button_6_down": {"number": 6, "pin": 21, "press": "down"},
}

running = True


def stop(*_: object) -> None:
    global running
    running = False


def main() -> None:
    signal.signal(signal.SIGINT, stop)
    buttons = []
    print("KoalaByte Blue RevA6 six-button test running. Press Ctrl+C to exit.")
    print("Hold button 3 for 3 seconds to test the shutdown-hold event; this script only prints the event.")
    for name, cfg in BUTTONS.items():
        number = int(cfg["number"])
        pin = int(cfg["pin"])
        press = str(cfg["press"])
        button = Button(pin, pull_up=True, bounce_time=0.05, hold_time=3.0)
        button.when_pressed = lambda n=name, num=number, p=pin, cmd=press: print(
            f"button={num} name={n} pin_bcm={p} event=press command={cmd}", flush=True
        )
        if "hold" in cfg:
            hold = str(cfg["hold"])
            button.when_held = lambda n=name, num=number, p=pin, cmd=hold: print(
                f"button={num} name={n} pin_bcm={p} event=hold command={cmd}", flush=True
            )
        buttons.append(button)
    while running:
        signal.pause()
    for button in buttons:
        button.close()


if __name__ == "__main__":
    main()
