from __future__ import annotations

import json
import queue
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class ButtonEvent:
    name: str
    command: str
    timestamp: float
    pin_bcm: int


DEFAULT_BUTTONS: Dict[str, Dict[str, object]] = {
    "back": {"pin": 5, "command": "back"},
    "select": {"pin": 6, "command": "scan"},
    "next": {"pin": 13, "command": "summary"},
    "menu": {"pin": 19, "command": "status"},
}


class GPIOButtonManager:
    """Front-panel Raspberry Pi GPIO button manager.

    Buttons are normally-open tactile switches. One side of each button goes to
    the assigned BCM GPIO pin and the other side goes to GND. The Pi internal
    pull-up is enabled through gpiozero.
    """

    def __init__(self, buttons: Optional[Dict[str, Dict[str, object]]] = None, log_path: str | Path = "logs/gpio_buttons.jsonl") -> None:
        self.buttons_config = buttons or DEFAULT_BUTTONS
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
                pin = int(cfg["pin"])
                command = str(cfg.get("command", name))
                button = Button(pin, pull_up=True, bounce_time=0.05)
                button.when_pressed = self._make_callback(name, command, pin)
                self._button_objs.append(button)
            self.available = True
        except Exception as exc:
            self.error = f"GPIO button init failed: {exc}"
            self.close()

    def _make_callback(self, name: str, command: str, pin: int):
        def _callback() -> None:
            event = ButtonEvent(name=name, command=command, timestamp=time.time(), pin_bcm=pin)
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
        payload = {
            "type": "gpio_button",
            "name": event.name,
            "command": event.command,
            "timestamp": event.timestamp,
            "pin_bcm": event.pin_bcm,
        }
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
