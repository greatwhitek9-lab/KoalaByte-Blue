#!/usr/bin/env python3
"""KoalaByte Blue RevA5 front-panel button test.

Wiring:
Back   -> BCM GPIO5  / physical pin 29
Select -> BCM GPIO6  / physical pin 31
Next   -> BCM GPIO13 / physical pin 33
Menu   -> BCM GPIO19 / physical pin 35
GND    -> physical pin 39 or any Pi GND
"""

from __future__ import annotations

import signal
from gpiozero import Button

PINS = {
    "back": 5,
    "select": 6,
    "next": 13,
    "menu": 19,
}

running = True


def stop(*_: object) -> None:
    global running
    running = False


def main() -> None:
    signal.signal(signal.SIGINT, stop)
    buttons = []
    print("KoalaByte Blue RevA5 button test running. Press Ctrl+C to exit.")
    for name, pin in PINS.items():
        button = Button(pin, pull_up=True, bounce_time=0.05)
        button.when_pressed = lambda n=name, p=pin: print(f"button={n} pin_bcm={p} pressed", flush=True)
        buttons.append(button)
    while running:
        signal.pause()
    for button in buttons:
        button.close()


if __name__ == "__main__":
    main()
