from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from .menu_catalog import make_menu_items


@dataclass
class MenuItem:
    label: str
    command: str
    description: str = ""
    enabled: bool = True


@dataclass
class MenuEvent:
    event_type: str
    command: str
    selected_index: int
    selected_label: str
    timestamp: float


@dataclass
class TouchConfig:
    row_height_px: int = 48
    long_press_seconds: float = 0.75
    scroll_threshold_px: int = 18


@dataclass
class TouchState:
    down_y: Optional[int] = None
    current_y: Optional[int] = None
    down_time: Optional[float] = None
    moved: bool = False


DEFAULT_MENU_ITEMS: List[MenuItem] = make_menu_items(MenuItem)


class MenuSelectionScreen:
    """Menu state machine for KoalaByte Blue.

    Inputs supported:
    - GPIO button commands from gpio_buttons.py: left/right/up/down/select/main_menu/back.
    - Touch scrolling through on_touch_down/on_touch_move/on_touch_up.
    - Touch long-press select.

    This class is display-backend agnostic. The ESP32-S3 display, terminal UI,
    or Pi touchscreen process can all render the same state. The default text
    rendering uses the RevA14 jungle/eucalyptus theme preview.
    """

    def __init__(
        self,
        items: Optional[Iterable[MenuItem]] = None,
        visible_rows: int = 6,
        touch_config: Optional[TouchConfig] = None,
        log_path: str | Path = "logs/menu_events.jsonl",
    ) -> None:
        self.items: List[MenuItem] = list(items or DEFAULT_MENU_ITEMS)
        if not self.items:
            raise ValueError("menu requires at least one item")
        self.visible_rows = max(1, visible_rows)
        self.touch_config = touch_config or TouchConfig()
        self.selected_index = 0
        self.scroll_offset = 0
        self.touch = TouchState()
        self.log_path = Path(log_path)
        self._handlers: Dict[str, Callable[[MenuItem], None]] = {}

    @property
    def selected_item(self) -> MenuItem:
        return self.items[self.selected_index]

    def register_handler(self, command: str, handler: Callable[[MenuItem], None]) -> None:
        self._handlers[command] = handler

    def handle_command(self, command: str) -> Optional[MenuEvent]:
        normalized = command.strip().lower()
        if normalized in {"up", "move_up"}:
            self.move(-1)
            return self._event("move", "up")
        if normalized in {"down", "move_down"}:
            self.move(1)
            return self._event("move", "down")
        if normalized in {"move_left", "left", "back"}:
            self.move(-1)
            return self._event("move", "left")
        if normalized in {"move_right", "right", "forward"}:
            self.move(1)
            return self._event("move", "right")
        if normalized in {"main_menu", "home"}:
            self.selected_index = 0
            self.scroll_offset = 0
            return self._event("home", "main_menu")
        if normalized in {"select", "enter"}:
            return self.select()
        if normalized == "shutdown":
            self._select_by_command("shutdown_confirm")
            return self.select()
        return self._event("ignored", normalized)

    def move(self, delta: int) -> None:
        if not self.items:
            return
        # Wrap around so the six front-panel buttons can browse the whole function list quickly.
        self.selected_index = (self.selected_index + delta) % len(self.items)
        self._clamp_scroll_to_selection()

    def select(self) -> MenuEvent:
        item = self.selected_item
        if not item.enabled:
            return self._event("disabled", item.command)
        event = self._event("select", item.command)
        handler = self._handlers.get(item.command)
        if handler:
            handler(item)
        return event

    def on_touch_down(self, y: int, now: Optional[float] = None) -> None:
        t = now if now is not None else time.time()
        self.touch = TouchState(down_y=y, current_y=y, down_time=t, moved=False)
        self._select_row_at_y(y)

    def on_touch_move(self, y: int, now: Optional[float] = None) -> Optional[MenuEvent]:
        if self.touch.down_y is None:
            return None
        self.touch.current_y = y
        delta = y - self.touch.down_y
        if abs(delta) < self.touch_config.scroll_threshold_px:
            return None
        rows = int(delta / self.touch_config.row_height_px)
        if rows == 0:
            rows = 1 if delta > 0 else -1
        self.touch.down_y = y
        self.touch.moved = True
        self.move(-rows)
        return self._event("touch_scroll", "touch_scroll")

    def on_touch_up(self, y: int, now: Optional[float] = None) -> Optional[MenuEvent]:
        t = now if now is not None else time.time()
        if self.touch.down_time is None:
            return None
        held = t - self.touch.down_time
        self._select_row_at_y(y)
        if held >= self.touch_config.long_press_seconds and not self.touch.moved:
            event = self.select()
            event.event_type = "touch_long_press_select"
            self._log_event(event)
        else:
            event = self._event("touch_tap", "touch_tap")
        self.touch = TouchState()
        return event

    def render_text(self) -> str:
        try:
            from .menu_theme import render_terminal_jungle_menu

            return render_terminal_jungle_menu(self)
        except Exception:
            return self._render_plain_text()

    def _render_plain_text(self) -> str:
        visible = self.visible_items()
        total = len(self.items)
        lines = ["KoalaByte Blue", f"Main Menu ({self.selected_index + 1}/{total})", ""]
        for absolute_index, item in visible:
            prefix = ">" if absolute_index == self.selected_index else " "
            disabled = " [locked]" if not item.enabled else ""
            lines.append(f"{prefix} {absolute_index + 1:02d}. {item.label}{disabled}")
            if absolute_index == self.selected_index and item.description:
                lines.append(f"    {item.description}")
        lines.append("")
        lines.append("Buttons: 1 menu | 2 left/back | 3 select/hold shutdown | 4 right | 5 up | 6 down")
        lines.append("Touch: drag to scroll | long press to select")
        return "\n".join(lines)

    def visible_items(self) -> List[tuple[int, MenuItem]]:
        end = min(len(self.items), self.scroll_offset + self.visible_rows)
        return list(enumerate(self.items[self.scroll_offset:end], start=self.scroll_offset))

    def _select_by_command(self, command: str) -> None:
        for idx, item in enumerate(self.items):
            if item.command == command:
                self.selected_index = idx
                self._clamp_scroll_to_selection()
                return

    def _select_row_at_y(self, y: int) -> None:
        row = max(0, y // self.touch_config.row_height_px)
        index = max(0, min(len(self.items) - 1, self.scroll_offset + row))
        self.selected_index = index
        self._clamp_scroll_to_selection()

    def _clamp_scroll_to_selection(self) -> None:
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.visible_rows:
            self.scroll_offset = self.selected_index - self.visible_rows + 1
        self.scroll_offset = max(0, min(self.scroll_offset, max(0, len(self.items) - self.visible_rows)))

    def _event(self, event_type: str, command: str) -> MenuEvent:
        event = MenuEvent(
            event_type=event_type,
            command=command,
            selected_index=self.selected_index,
            selected_label=self.selected_item.label,
            timestamp=time.time(),
        )
        self._log_event(event)
        return event

    def _log_event(self, event: MenuEvent) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")
