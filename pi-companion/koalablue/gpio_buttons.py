from __future__ import annotations

import json
import queue
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class ButtonEvent:
    number: int
    name: str
    label: str
    command: str
    event_type: str
    timestamp: float
    pin_bcm: int


@dataclass(frozen=True)
class ButtonElectricalMode:
    pull_up: bool = True
    idle_state: str = "HIGH"
    pressed_state: str = "LOW"
    wiring: str = "8-key module VCC to Pi 3.3V, GND to Pi GND, K1-K8 to assigned BCM GPIO inputs"


DEFAULT_ELECTRICAL_MODE = ButtonElectricalMode()


DEFAULT_BUTTONS: Dict[str, Dict[str, object]] = {
    "button_1": {"number": 1, "module_key": "K1", "label": "Main Menu", "pin": 5, "physical_pin": 29, "press_command": "main_menu"},
    "button_2": {"number": 2, "module_key": "K2", "label": "Move Left / Back", "pin": 6, "physical_pin": 31, "press_command": "move_left", "alias_command": "back"},
    "button_3": {"number": 3, "module_key": "K3", "label": "Enter / Select", "pin": 13, "physical_pin": 33, "press_command": "select"},
    "button_4": {"number": 4, "module_key": "K4", "label": "Move Right / Forward", "pin": 19, "physical_pin": 35, "press_command": "move_right", "alias_command": "forward"},
    "button_5": {"number": 5, "module_key": "K5", "label": "Up", "pin": 26, "physical_pin": 37, "press_command": "up"},
    "button_6": {"number": 6, "module_key": "K6", "label": "Down", "pin": 21, "physical_pin": 40, "press_command": "down"},
    "button_7": {"number": 7, "module_key": "K7", "label": "PWR On/Off", "pin": 20, "physical_pin": 38, "press_command": "pwr_toggle"},
    "button_8": {"number": 8, "module_key": "K8", "label": "Reset", "pin": 16, "physical_pin": 36, "press_command": "reset"},
}


class GPIOButtonManager:
    def __init__(self, buttons: Optional[Dict[str, Dict[str, object]]] = None, log_path: str | Path = "logs/gpio_buttons.jsonl", electrical_mode: ButtonElectricalMode = DEFAULT_ELECTRICAL_MODE) -> None:
        self.buttons_config = buttons or DEFAULT_BUTTONS
        self.electrical_mode = electrical_mode
        self.log_path = Path(log_path)
        self.events: "queue.Queue[ButtonEvent]" = queue.Queue()
        self._button_objs = []
        self.available = False
        self.error: Optional[str] = None

    def start(self) -> None:
        try:
            from gpiozero import Button  # type: ignore
        except Exception as exc:
            self.error = f"gpiozero unavailable: {exc}"
            return
        try:
            for name, cfg in self.buttons_config.items():
                pin = int(cfg.get("pin", cfg.get("pin_bcm")))
                number = int(cfg.get("number", 0))
                label = str(cfg.get("label", name))
                press_command = str(cfg.get("press_command", cfg.get("command", name)))
                hold_seconds = float(cfg.get("hold_seconds", 3.0))
                bounce_time = float(cfg.get("bounce_time", 0.05))
                pull_up = bool(cfg.get("pull_up", self.electrical_mode.pull_up))
                button = Button(pin, pull_up=pull_up, bounce_time=bounce_time, hold_time=hold_seconds)
                button.when_pressed = self._make_callback(number=number, name=name, label=label, command=press_command, event_type="press", pin=pin)
                self._button_objs.append(button)
            self.available = True
        except Exception as exc:
            self.error = f"GPIO button init failed: {exc}"
            self.close()

    def _make_callback(self, *, number: int, name: str, label: str, command: str, event_type: str, pin: int):
        def _callback() -> None:
            event = ButtonEvent(number=number, name=name, label=label, command=command, event_type=event_type, timestamp=time.time(), pin_bcm=pin)
            self.events.put(event)
            self._log(event)
        return _callback

    def get_event(self, timeout: float = 0.0) -> Optional[ButtonEvent]:
        try:
            return self.events.get(timeout=timeout)
        except queue.Empty:
            return None

    def _log(self, event: ButtonEvent) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"type": "gpio_button", "button_number": event.number, "name": event.name, "label": event.label, "command": event.command, "event_type": event.event_type, "timestamp": event.timestamp, "pin_bcm": event.pin_bcm, "pull_up": self.electrical_mode.pull_up, "idle_state": self.electrical_mode.idle_state, "pressed_state": self.electrical_mode.pressed_state, "wiring": self.electrical_mode.wiring}
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")

    def close(self) -> None:
        for button in self._button_objs:
            try:
                button.close()
            except Exception:
                pass
        self._button_objs.clear()
        self.available = False
