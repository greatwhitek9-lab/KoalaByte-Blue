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
    held_seconds: float = 0.0
    requires_hold: bool = False


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
    "button_7": {
        "number": 7,
        "module_key": "K7",
        "label": "Safe Shutdown",
        "pin": 20,
        "physical_pin": 38,
        "press_command": "power_toggle",
        "requires_hold": True,
        "hold_seconds": 2.5,
    },
    "button_8": {
        "number": 8,
        "module_key": "K8",
        "label": "Reset / Reboot",
        "pin": 16,
        "physical_pin": 36,
        "press_command": "reset",
        "requires_hold": True,
        "hold_seconds": 3.0,
    },
}


class GPIOButtonManager:
    def __init__(
        self,
        buttons: Optional[Dict[str, Dict[str, object]]] = None,
        log_path: str | Path = "logs/gpio_buttons.jsonl",
        electrical_mode: ButtonElectricalMode = DEFAULT_ELECTRICAL_MODE,
    ) -> None:
        self.buttons_config = buttons or DEFAULT_BUTTONS
        self.electrical_mode = electrical_mode
        self.log_path = Path(log_path)
        self.events: "queue.Queue[ButtonEvent]" = queue.Queue()
        self._button_objs = []
        self.available = False
        self.error: Optional[str] = None
        self.control_mode = "auto"

    def _record_touch_speech_fallback(self, reason: str) -> None:
        try:
            from .control_mode import write_control_mode

            write_control_mode(
                "touch_speech_only",
                reason=reason,
                source="gpio_button_manager",
                buttons_available=False,
                extra={"gpio_error": reason},
            )
            self.control_mode = "touch_speech_only"
        except Exception:
            pass

    def start(self) -> None:
        try:
            from .control_mode import effective_control_mode, gpio_buttons_enabled

            self.control_mode = effective_control_mode()
            if not gpio_buttons_enabled():
                self.error = "GPIO buttons disabled by touch_speech_only control mode"
                return
        except Exception:
            self.control_mode = "auto"

        try:
            from gpiozero import Button  # type: ignore
        except Exception as exc:
            self.error = f"gpiozero unavailable: {exc}"
            self._record_touch_speech_fallback(self.error)
            return

        try:
            for name, cfg in self.buttons_config.items():
                pin = int(cfg.get("pin", cfg.get("pin_bcm")))
                number = int(cfg.get("number", 0))
                label = str(cfg.get("label", name))
                press_command = str(cfg.get("press_command", cfg.get("command", name)))
                requires_hold = bool(cfg.get("requires_hold", number in {7, 8}))
                hold_seconds = float(cfg.get("hold_seconds", 3.0 if requires_hold else 1.0))
                bounce_time = float(cfg.get("bounce_time", 0.05))
                pull_up = bool(cfg.get("pull_up", self.electrical_mode.pull_up))

                button = Button(
                    pin,
                    pull_up=pull_up,
                    bounce_time=bounce_time,
                    hold_time=hold_seconds,
                    hold_repeat=False,
                )
                callback = self._make_callback(
                    number=number,
                    name=name,
                    label=label,
                    command=press_command,
                    event_type="hold" if requires_hold else "press",
                    pin=pin,
                    held_seconds=hold_seconds if requires_hold else 0.0,
                    requires_hold=requires_hold,
                )
                if requires_hold:
                    button.when_held = callback
                else:
                    button.when_pressed = callback
                self._button_objs.append(button)

            self.available = True
            self.control_mode = "full_controls"
            try:
                from .control_mode import write_control_mode

                write_control_mode(
                    "full_controls",
                    reason="All K1-K8 GPIO inputs initialized successfully; K7/K8 destructive commands require a deliberate hold.",
                    source="gpio_button_manager",
                    buttons_available=True,
                    extra={
                        "protected_buttons": {
                            "K7": {"command": "power_toggle", "label": "Safe Shutdown", "hold_seconds": 2.5},
                            "K8": {"command": "reset", "label": "Reset / Reboot", "hold_seconds": 3.0},
                        }
                    },
                )
            except Exception:
                pass
        except Exception as exc:
            self.error = f"GPIO button init failed: {exc}"
            self.close()
            self._record_touch_speech_fallback(self.error)

    def _make_callback(
        self,
        *,
        number: int,
        name: str,
        label: str,
        command: str,
        event_type: str,
        pin: int,
        held_seconds: float,
        requires_hold: bool,
    ):
        def _callback() -> None:
            event = ButtonEvent(
                number=number,
                name=name,
                label=label,
                command=command,
                event_type=event_type,
                timestamp=time.time(),
                pin_bcm=pin,
                held_seconds=held_seconds,
                requires_hold=requires_hold,
            )
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
            "button_number": event.number,
            "name": event.name,
            "label": event.label,
            "command": event.command,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "pin_bcm": event.pin_bcm,
            "held_seconds": event.held_seconds,
            "requires_hold": event.requires_hold,
            "pull_up": self.electrical_mode.pull_up,
            "idle_state": self.electrical_mode.idle_state,
            "pressed_state": self.electrical_mode.pressed_state,
            "wiring": self.electrical_mode.wiring,
            "control_mode": self.control_mode,
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
