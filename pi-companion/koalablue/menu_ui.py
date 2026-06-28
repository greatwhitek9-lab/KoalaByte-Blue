from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from .menu_catalog import make_menu_items, submenu_name_from_command, submenu_title
from .meshtastic_menu_items import make_didgeridoo_items, make_meshtastic_items


@dataclass
class MenuItem:
    label: str
    command: str
    description: str = ""
    enabled: bool = True
    group: str = "System / Companion"


@dataclass
class MenuEvent:
    event_type: str
    command: str
    selected_index: int
    selected_label: str
    selected_group: str
    timestamp: float


@dataclass
class TouchConfig:
    row_height_px: int = 48
    long_press_seconds: float = 0.75
    scroll_threshold_px: int = 18
    double_tap_seconds: float = 0.45


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
    - Touch double-tap menu reopen while the AI face is showing.
    - Hierarchical submenus through commands like submenu:eucalyptus and submenu:lab.

    The menu, GPIO buttons, touchscreen, Heltec/T114 display path, and ESP32-S3
    DualEye bridge all share this highlighted-item state. All action execution
    goes through select(), so B3/select and touchscreen long-press run the same
    highlighted menu item.
    """

    def __init__(
        self,
        items: Optional[Iterable[MenuItem]] = None,
        visible_rows: int = 6,
        touch_config: Optional[TouchConfig] = None,
        log_path: str | Path = "logs/menu_events.jsonl",
    ) -> None:
        self.menu_name = "main"
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
        self.display_mode = "menu"
        self.face_state = "idle"
        self.face_message = "KillerKoala is watching the canopy"
        self.idle_face_seconds = 30
        self.last_input_at = time.time()
        self._last_tap_at = 0.0

    @property
    def menu_title(self) -> str:
        if self.menu_name == "meshtastic":
            return "Meshtastic App"
        return submenu_title(self.menu_name)

    @property
    def selected_item(self) -> MenuItem:
        return self.items[self.selected_index]

    @property
    def selected_group(self) -> str:
        return self.selected_item.group

    @property
    def menu_visible(self) -> bool:
        return self.display_mode == "menu"

    def register_handler(self, command: str, handler: Callable[[MenuItem], None]) -> None:
        self._handlers[command] = handler

    def handle_command(self, command: str) -> Optional[MenuEvent]:
        normalized = command.strip().lower()
        now = time.time()

        if normalized in {"main_menu", "home", "menu"}:
            self.last_input_at = now
            return self.reopen_menu("main_menu")

        if self.display_mode != "menu":
            return self._event("ai_face_waiting_for_menu", normalized)

        self.last_input_at = now
        if normalized in {"up", "move_up"}:
            self.move(-1)
            return self._event("move", "up")
        if normalized in {"down", "move_down"}:
            self.move(1)
            return self._event("move", "down")
        if normalized in {"move_left", "left", "back"}:
            if self.menu_name == "meshtastic":
                return self._open_menu("didgeridoo", "submenu_back", "submenu:didgeridoo")
            if self.menu_name != "main":
                return self._open_menu("main", "submenu_back", "submenu:main")
            self.move(-1)
            return self._event("move", "left")
        if normalized in {"move_right", "right", "forward"}:
            self.move(1)
            return self._event("move", "right")
        if normalized in {"select", "enter"}:
            return self.select("select")
        if normalized == "shutdown":
            self._select_by_command("shutdown_confirm")
            return self.select("select")
        return self._event("ignored", normalized)

    def move(self, delta: int) -> None:
        if not self.items:
            return
        self.selected_index = (self.selected_index + delta) % len(self.items)
        self._clamp_scroll_to_selection()

    def _run_selected_handler(self, item: MenuItem, select_event_type: str) -> MenuEvent:
        event = self._event(select_event_type, item.command)
        handler = self._handlers.get(item.command)
        self.show_ai_face("action_running", f"Running {item.label}", log_event_type="action_running")
        try:
            if handler:
                handler(item)
            else:
                from .menu_action_runner import run_automated_menu_action

                run_automated_menu_action(item.command, item.label, item.group)
        except Exception:
            self.show_ai_face("error", f"{item.label} hit a snag", log_event_type="action_error")
            raise
        self.show_ai_face("action_complete", f"{item.label} complete", log_event_type="action_complete")
        return event

    def select(self, select_event_type: str = "select") -> MenuEvent:
        if self.display_mode != "menu":
            return self._event("ai_face_waiting_for_menu", select_event_type)
        item = self.selected_item
        if not item.enabled:
            return self._event("disabled", item.command)
        if item.command == "meshtastic_app":
            return self._open_menu("meshtastic", "submenu_open", "submenu:meshtastic")
        submenu = submenu_name_from_command(item.command)
        if submenu:
            return self._open_menu(submenu, "submenu_open" if submenu != "main" else "submenu_back", item.command)
        return self._run_selected_handler(item, select_event_type)

    def show_ai_face(self, state: str = "idle", message: str = "KillerKoala is watching the canopy", *, log_event_type: str = "ai_face") -> MenuEvent:
        self.display_mode = "ai_face"
        self.face_state = state
        self.face_message = message
        event = self._make_event(log_event_type, state)
        self._log_event(event)
        return event

    def reopen_menu(self, reason: str = "main_menu") -> MenuEvent:
        self.display_mode = "menu"
        self.face_state = "menu"
        self.face_message = "Menu open"
        self.last_input_at = time.time()
        if reason in {"main_menu", "home", "touch_double_tap_menu"}:
            return self._open_menu("main", "menu_reopen", reason)
        return self._event("menu_reopen", reason)

    def check_idle_timeout(self, now: Optional[float] = None) -> Optional[MenuEvent]:
        if self.display_mode != "menu":
            return None
        t = now if now is not None else time.time()
        if t - self.last_input_at >= self.idle_face_seconds:
            return self.show_ai_face("idle", "KillerKoala idle — press B1/menu or double-tap to reopen", log_event_type="idle_timeout")
        return None

    def on_touch_down(self, y: int, now: Optional[float] = None) -> None:
        t = now if now is not None else time.time()
        self.touch = TouchState(down_y=y, current_y=y, down_time=t, moved=False)
        if self.display_mode == "menu":
            self.last_input_at = t
            self._select_row_at_y(y)
            self._log_event(self._make_event("touch_highlight", "touch_down"))

    def on_touch_move(self, y: int, now: Optional[float] = None) -> Optional[MenuEvent]:
        if self.touch.down_y is None:
            return None
        self.touch.current_y = y
        if self.display_mode != "menu":
            return None
        delta = y - self.touch.down_y
        if abs(delta) < self.touch_config.scroll_threshold_px:
            return None
        rows = int(delta / self.touch_config.row_height_px)
        if rows == 0:
            rows = 1 if delta > 0 else -1
        self.touch.down_y = y
        self.touch.moved = True
        self.last_input_at = now if now is not None else time.time()
        self.move(-rows)
        return self._event("touch_scroll", "touch_scroll")

    def on_touch_up(self, y: int, now: Optional[float] = None) -> Optional[MenuEvent]:
        t = now if now is not None else time.time()
        if self.touch.down_time is None:
            return None
        held = t - self.touch.down_time

        if self.display_mode != "menu":
            self.touch = TouchState()
            if t - self._last_tap_at <= self.touch_config.double_tap_seconds:
                self._last_tap_at = 0.0
                return self.reopen_menu("touch_double_tap_menu")
            self._last_tap_at = t
            return self._event("ai_face_touch_tap", "touch_tap")

        self.last_input_at = t
        self._select_row_at_y(y)
        if held >= self.touch_config.long_press_seconds and not self.touch.moved:
            event = self.select("touch_long_press_select")
        else:
            event = self._event("touch_tap", "touch_tap")
        self.touch = TouchState()
        return event

    def render_text(self) -> str:
        self.check_idle_timeout()
        if self.display_mode != "menu":
            return self._render_ai_face_text()
        try:
            from .menu_theme import render_terminal_jungle_menu
            return render_terminal_jungle_menu(self)
        except Exception:
            return self._render_plain_text()

    def _render_ai_face_text(self) -> str:
        lines = [
            "🌿════════════════════════════════════════════════════════════════════════🌿",
            "                         KILLERKOALA AI FACE                         ",
            "🌿════════════════════════════════════════════════════════════════════════🌿",
            f"  State: {self.face_state}",
            f"  Message: {self.face_message}",
            "",
            "  Menu is hidden. Press B1/Menu or double-tap touchscreen to reopen.",
            "🌿════════════════════════════════════════════════════════════════════════🌿",
        ]
        return "\n".join(lines)

    def _render_plain_text(self) -> str:
        visible = self.visible_items()
        total = len(self.items)
        lines = ["KoalaByte Blue", f"{self.menu_title} / {self.selected_group} ({self.selected_index + 1}/{total})", ""]
        previous_group: Optional[str] = None
        for absolute_index, item in visible:
            if item.group != previous_group:
                lines.append(f"[{item.group}]")
                previous_group = item.group
            prefix = "●" if item.command.startswith("status:") else (">" if absolute_index == self.selected_index else " ")
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
        return [(idx, self._display_item(item)) for idx, item in enumerate(self.items[self.scroll_offset:end], start=self.scroll_offset)]

    def _display_item(self, item: MenuItem) -> MenuItem:
        if not item.command.startswith("status:"):
            return item
        try:
            from .t114_menu_status import status_label_description

            label, description = status_label_description(item.command)
            return MenuItem(label=label, command=item.command, description=description or item.description, enabled=item.enabled, group=item.group)
        except Exception as exc:
            return MenuItem(label=f"{item.label}: Unknown", command=item.command, description=f"Status unavailable: {exc}", enabled=item.enabled, group=item.group)

    def _open_menu(self, menu_name: str, event_type: str, command: str) -> MenuEvent:
        target = "main" if menu_name == "main" else menu_name
        if target == "meshtastic":
            new_items = make_meshtastic_items(MenuItem)
        elif target == "didgeridoo":
            new_items = make_didgeridoo_items(MenuItem)
        else:
            new_items = make_menu_items(MenuItem, target)
        if new_items:
            self.display_mode = "menu"
            self.menu_name = target
            self.items = new_items
            self.selected_index = 0
            self.scroll_offset = 0
            self.touch = TouchState()
            self.last_input_at = time.time()
        return self._event(event_type, command)

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

    def _make_event(self, event_type: str, command: str) -> MenuEvent:
        return MenuEvent(
            event_type=event_type,
            command=command,
            selected_index=self.selected_index,
            selected_label=self._display_item(self.selected_item).label,
            selected_group=self.selected_group,
            timestamp=time.time(),
        )

    def _event(self, event_type: str, command: str) -> MenuEvent:
        event = self._make_event(event_type, command)
        self._log_event(event)
        return event

    def _log_event(self, event: MenuEvent) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")
        try:
            from .menu_display_sync import sync_ai_face_display, sync_menu_state

            if self.display_mode == "menu":
                sync_menu_state(self, event)
            else:
                sync_ai_face_display(self, event, state=self.face_state, message=self.face_message)
        except Exception:
            pass
