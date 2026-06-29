from __future__ import annotations

import json
import queue
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .gpio_buttons import ButtonEvent, GPIOButtonManager
from .menu_catalog import make_menu_items


@dataclass(frozen=True)
class MenuItem:
    label: str
    command: str
    description: str = ""
    enabled: bool = True


@dataclass
class MenuState:
    title: str = "KoalaByte Blue"
    selected_index: int = 0
    scroll_offset: int = 0
    visible_rows: int = 7
    last_action: str = "ready"
    last_selected: Optional[MenuItem] = None


DEFAULT_MENU_ITEMS: List[MenuItem] = make_menu_items(MenuItem)


class MenuController:
    """Selection model shared by GPIO, keyboard, and touchscreen front ends."""

    def __init__(self, items: Optional[Iterable[MenuItem]] = None, state: Optional[MenuState] = None) -> None:
        self.items: List[MenuItem] = list(items or DEFAULT_MENU_ITEMS)
        if not self.items:
            raise ValueError("menu requires at least one item")
        self.state = state or MenuState()
        self._clamp()

    @property
    def selected_index(self) -> int:
        return self.state.selected_index

    @property
    def scroll_offset(self) -> int:
        return self.state.scroll_offset

    @property
    def visible_rows(self) -> int:
        return self.state.visible_rows

    @property
    def touch_config(self):
        class _TouchConfig:
            row_height_px = 48
            long_press_seconds = 0.75
            scroll_threshold_px = 18

        return _TouchConfig()

    def handle_command(self, command: str) -> Optional[MenuItem]:
        command = command.strip().lower()
        selected: Optional[MenuItem] = None
        if command in {"up", "move_up", "scroll_up"}:
            self.move(-1)
        elif command in {"down", "move_down", "scroll_down"}:
            self.move(1)
        elif command in {"move_left", "left", "back"}:
            self.move(-1)
            self.state.last_action = "move_left"
        elif command in {"move_right", "right", "forward"}:
            self.move(1)
            self.state.last_action = "move_right"
        elif command in {"select", "enter", "touch_select", "long_press_select"}:
            selected = self.select()
        elif command in {"main_menu", "home"}:
            self.state.selected_index = 0
            self.state.scroll_offset = 0
            self.state.last_action = "main_menu"
        elif command in {"shutdown", "power", "power_toggle", "power_on_off"}:
            self._select_by_command("shutdown_confirm")
            selected = self.select()
        elif command in {"reset", "reboot", "reset_reboot"}:
            self._select_by_command("reset_confirm")
            selected = self.select()
        else:
            self.state.last_action = f"ignored:{command}"
        self._clamp()
        return selected

    def move(self, delta: int) -> None:
        self.state.selected_index = (self.state.selected_index + delta) % len(self.items)
        self.state.last_action = "move"
        self._clamp_scroll()

    def select(self) -> Optional[MenuItem]:
        item = self.items[self.state.selected_index]
        if not item.enabled:
            self.state.last_selected = None
            self.state.last_action = f"disabled:{item.command}"
            return None
        self.state.last_selected = item
        self.state.last_action = f"select:{item.command}"
        return item

    def touch_scroll(self, delta_rows: int) -> None:
        self.move(delta_rows)
        self.state.last_action = "touch_scroll"

    def visible_items(self) -> List[tuple[int, MenuItem]]:
        start = self.state.scroll_offset
        end = min(len(self.items), start + self.state.visible_rows)
        return list(enumerate(self.items[start:end], start=start))

    def render_text(self) -> str:
        try:
            from .menu_theme import render_terminal_jungle_menu

            themed = render_terminal_jungle_menu(self)
            return f"{themed}\nLast: {self.state.last_action}"
        except Exception:
            return self._render_plain_text()

    def _render_plain_text(self) -> str:
        lines = [f"=== {self.state.title} ===", f"Function Menu ({self.state.selected_index + 1}/{len(self.items)})", ""]
        for index, item in self.visible_items():
            cursor = ">" if index == self.state.selected_index else " "
            disabled = " [locked]" if not item.enabled else ""
            lines.append(f"{cursor} {index + 1:02d}. {item.label}{disabled}")
            if index == self.state.selected_index and item.description:
                lines.append(f"     {item.description}")
        lines.extend([
            "",
            "Buttons: K1 menu | K2 previous/back | K3 select | K4 next | K5 up | K6 down | K7 power off | K8 reset/reboot",
            "Touch: scroll list | long press item to select",
            f"Last: {self.state.last_action}",
        ])
        return "\n".join(lines)

    def _select_by_command(self, command: str) -> None:
        for idx, item in enumerate(self.items):
            if item.command == command:
                self.state.selected_index = idx
                self._clamp_scroll()
                return

    def _clamp(self) -> None:
        self.state.selected_index = max(0, min(self.state.selected_index, len(self.items) - 1))
        self._clamp_scroll()

    def _clamp_scroll(self) -> None:
        if self.state.selected_index < self.state.scroll_offset:
            self.state.scroll_offset = self.state.selected_index
        max_visible = self.state.scroll_offset + self.state.visible_rows - 1
        if self.state.selected_index > max_visible:
            self.state.scroll_offset = self.state.selected_index - self.state.visible_rows + 1
        max_offset = max(0, len(self.items) - self.state.visible_rows)
        self.state.scroll_offset = max(0, min(self.state.scroll_offset, max_offset))


class MenuEventLog:
    def __init__(self, path: str | Path = "logs/menu_events.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event_type: str, payload: Dict[str, object]) -> None:
        row = {"timestamp": time.time(), "event_type": event_type, **payload}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


class ButtonMenuAdapter:
    """Adapter that maps GPIO button events into menu commands."""

    def __init__(self, controller: MenuController, button_manager: Optional[GPIOButtonManager] = None, event_log: Optional[MenuEventLog] = None) -> None:
        self.controller = controller
        self.button_manager = button_manager or GPIOButtonManager()
        self.event_log = event_log or MenuEventLog()

    def start(self) -> None:
        self.button_manager.start()

    def poll_once(self, timeout: float = 0.0) -> Optional[MenuItem]:
        event = self.button_manager.get_event(timeout=timeout)
        if event is None:
            return None
        return self.handle_button_event(event)

    def handle_button_event(self, event: ButtonEvent) -> Optional[MenuItem]:
        selected = self.controller.handle_command(event.command)
        self.event_log.write(
            "button_menu_event",
            {
                "button_number": event.number,
                "button_label": event.label,
                "command": event.command,
                "menu_action": self.controller.state.last_action,
                "selected": selected.label if selected else None,
            },
        )
        return selected


class TouchMenuAdapter:
    """Touch handling abstraction.

    Touch screens usually appear as pointer input on the Pi desktop. The pygame
    loop is optional; the pure controller methods can also be called from any UI
    toolkit. A long press on a row emits select. Vertical drag emits scroll.
    """

    def __init__(self, controller: MenuController, long_press_seconds: float = 0.75, row_height: int = 44, event_log: Optional[MenuEventLog] = None) -> None:
        self.controller = controller
        self.long_press_seconds = long_press_seconds
        self.row_height = row_height
        self.event_log = event_log or MenuEventLog()
        self._touch_down_at: Optional[float] = None
        self._touch_down_y: Optional[int] = None
        self._touch_down_index: Optional[int] = None

    def touch_down(self, y: int) -> None:
        self._touch_down_at = time.time()
        self._touch_down_y = y
        self._touch_down_index = self._row_to_index(y)

    def touch_move(self, y: int) -> None:
        if self._touch_down_y is None:
            return
        delta = y - self._touch_down_y
        if abs(delta) >= self.row_height:
            rows = -int(delta / self.row_height)
            self.controller.touch_scroll(rows)
            self._touch_down_y = y
            self.event_log.write("touch_scroll", {"rows": rows, "selected_index": self.controller.state.selected_index})

    def touch_up(self, y: int) -> Optional[MenuItem]:
        if self._touch_down_at is None:
            return None
        held = time.time() - self._touch_down_at
        index = self._row_to_index(y)
        selected: Optional[MenuItem] = None
        if held >= self.long_press_seconds and index is not None:
            self.controller.state.selected_index = index
            selected = self.controller.handle_command("long_press_select")
        elif index is not None:
            self.controller.state.selected_index = index
            self.controller.state.last_action = "touch_focus"
        self.event_log.write(
            "touch_up",
            {"held_seconds": held, "row_index": index, "selected": selected.label if selected else None},
        )
        self._touch_down_at = None
        self._touch_down_y = None
        self._touch_down_index = None
        return selected

    def _row_to_index(self, y: int) -> Optional[int]:
        row = max(0, int(y / self.row_height) - 1)
        index = self.controller.state.scroll_offset + row
        if 0 <= index < len(self.controller.items):
            return index
        return None


def run_text_menu_once(command: Optional[str] = None) -> str:
    controller = MenuController()
    if command:
        controller.handle_command(command)
    return controller.render_text()


def run_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="KoalaByte Blue menu selection screen")
    parser.add_argument("--command", default=None, help="Optional single command to apply before rendering")
    args = parser.parse_args()
    print(run_text_menu_once(args.command))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
