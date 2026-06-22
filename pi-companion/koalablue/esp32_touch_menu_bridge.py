from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .menu_ui import MenuEvent, MenuSelectionScreen, TouchConfig


@dataclass
class TouchBridgeEvent:
    raw: dict
    menu_event: Optional[dict]
    timestamp: float


class Esp32TouchMenuBridge:
    """Translate ESP32-S3 DualEye menu_touch JSON into MenuSelectionScreen events.

    The bridge keeps touch semantics on the Pi menu state machine while the ESP32 owns
    raw/calibrated touch sampling. Buttons still work because this does not replace
    GPIO input; it only adds another event source.
    """

    def __init__(self, menu: Optional[MenuSelectionScreen] = None, log_path: str | Path = "logs/esp32_touch_menu_events.jsonl") -> None:
        self.menu = menu or MenuSelectionScreen(touch_config=TouchConfig(row_height_px=40, long_press_seconds=0.75, scroll_threshold_px=18))
        self.log_path = Path(log_path)

    def handle_payload(self, payload: dict) -> Optional[MenuEvent]:
        if payload.get("type") != "menu_touch":
            return None
        event_name = str(payload.get("event") or "tap")
        y = int(payload.get("y") or 0)
        event: Optional[MenuEvent]
        if event_name == "down":
            self.menu.on_touch_down(y)
            event = None
        elif event_name == "move":
            event = self.menu.on_touch_move(y)
        elif event_name in {"up", "tap"}:
            event = self.menu.on_touch_up(y)
        elif event_name in {"long_press", "long_press_select"}:
            self.menu.on_touch_down(y, now=time.time() - self.menu.touch_config.long_press_seconds - 0.05)
            event = self.menu.on_touch_up(y)
        else:
            event = self.menu.handle_command(str(payload.get("command") or "touch_event"))
        self._log(payload, event)
        return event

    def handle_line(self, line: str) -> Optional[MenuEvent]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return None
        return self.handle_payload(payload)

    def calibration_command(self, *, screen_w: int = 240, screen_h: int = 240, row_height: int = 40, visible_rows: int = 6) -> str:
        return json.dumps({
            "type": "menu_frame",
            "screen_w": screen_w,
            "screen_h": screen_h,
            "row_height": row_height,
            "visible_rows": visible_rows,
        })

    def _log(self, payload: dict, event: Optional[MenuEvent]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        record = TouchBridgeEvent(raw=payload, menu_event=asdict(event) if event else None, timestamp=time.time())
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(record), sort_keys=True) + "\n")
