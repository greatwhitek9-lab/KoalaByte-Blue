#!/usr/bin/env python3
"""Run the Pi-owned KoalaByte menu/control state machine without a local display."""

from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path

from koalablue.bounded_log import append_jsonl
from koalablue.gpio_buttons import GPIOButtonManager
from koalablue.hdmi_display_state import drain_menu_commands
from koalablue.killerkoala_error_dig import run_standalone_error_sequence
from koalablue.killerkoala_runtime_limits import install_killerkoala_runtime_limits
from koalablue.menu_display_sync import sync_ai_face_display, sync_menu_state
from koalablue.persistent_action_runtime import install_persistent_action_runtime
from koalablue.persistent_action_state import active_actions
from koalablue.runtime_serial_ownership import install_display_command_clients
from scripts.run_menu_screen import make_menu, open_submenu

STATUS_PATH = Path("logs/runtime/headless_menu_status.json")
EVENT_PATH = Path("logs/runtime/headless_menu_events.jsonl")
MENU_COMMAND_MAX_AGE_SECONDS = max(
    0.5,
    min(float(os.getenv("KOALABYTE_MENU_COMMAND_MAX_AGE_SECONDS", "3.0")), 30.0),
)

install_killerkoala_runtime_limits()
install_persistent_action_runtime()


def write_status(status: str, **extra: object) -> None:
    payload = {
        "status": status,
        "mode": "headless_pi_control",
        "local_graphical_display_required": False,
        "gpio_buttons": "K1-K8",
        "serial_transport": "single_owner_command_bus",
        "low_memory_ai_limits": True,
        "persistent_actions": active_actions(),
        "updated_at": time.time(),
        **extra,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATUS_PATH.with_name(f".{STATUS_PATH.name}.tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(STATUS_PATH)


def append_event(payload: dict[str, object]) -> None:
    append_jsonl(EVENT_PATH, payload)


def sync_current_display(menu: object, event: object | None = None) -> dict[str, object]:
    """Publish the current Pi-owned menu/face state after every runtime transition."""
    if str(getattr(menu, "display_mode", "menu")) == "ai_face":
        return sync_ai_face_display(
            menu,
            event,
            state=str(getattr(menu, "face_state", "idle")),
            message=str(getattr(menu, "face_message", "KillerKoala is watching the canopy")),
        )
    return sync_menu_state(menu, event)


def dispatch_live_menu_command(menu: object, command: str):
    """Dispatch GPIO/HDMI/voice commands through the one live menu state machine."""

    clean = str(command or "").strip()
    if clean.startswith("submenu:"):
        if not open_submenu(menu, clean):
            raise RuntimeError(f"submenu target not available: {clean}")
        menu.display_mode = "menu"
        menu.face_state = "menu"
        menu.face_message = f"{menu.menu_title} open"
        menu.last_input_at = time.time()
        return menu._event("submenu_voice_open", clean)
    return menu.handle_command(clean)


def _fresh_queued_request(request: dict[str, object]) -> bool:
    submitted = request.get("submitted_at")
    try:
        age = max(0.0, time.time() - float(submitted))
    except (TypeError, ValueError):
        age = 0.0
    if age <= MENU_COMMAND_MAX_AGE_SECONDS:
        return True
    append_event(
        {
            "type": "stale_menu_command_dropped",
            "command": str(request.get("command") or ""),
            "source": str(request.get("source") or "hdmi"),
            "submitted_at": submitted,
            "age_seconds": round(age, 3),
            "max_age_seconds": MENU_COMMAND_MAX_AGE_SECONDS,
            "timestamp": time.time(),
        }
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run KoalaByte headless K1-K8 menu and display synchronization"
    )
    parser.add_argument("--poll-seconds", type=float, default=0.05)
    args = parser.parse_args()

    install_display_command_clients()

    stop_requested = False

    def stop_handler(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    menu = make_menu()
    buttons = GPIOButtonManager(
        log_path="logs/gpio_buttons/gpio_button_runtime_events.jsonl"
    )
    buttons.start()

    write_status(
        "HEADLESS_MENU_STARTING",
        buttons_available=buttons.available,
        button_error=buttons.error,
        selected_label=menu.selected_item.label,
    )
    sync_current_display(menu, menu.reopen_menu("main_menu"))

    try:
        while not stop_requested:
            button_event = buttons.get_event(timeout=max(0.01, args.poll_seconds))
            event_payload: dict[str, object] | None = None
            command = ""
            if button_event is not None:
                event_payload = {
                    "type": "gpio_button_dispatch",
                    "button_number": button_event.number,
                    "command": button_event.command,
                    "event_type": button_event.event_type,
                    "requires_hold": button_event.requires_hold,
                    "held_seconds": button_event.held_seconds,
                    "timestamp": time.time(),
                }
                command = button_event.command
            else:
                queued = drain_menu_commands(max_items=1)
                if queued:
                    request = queued[0]
                    if not _fresh_queued_request(request):
                        continue
                    command = str(request.get("command") or "").strip()
                    event_payload = {
                        "type": "hdmi_menu_command_dispatch",
                        "command": command,
                        "source": str(request.get("source") or "hdmi"),
                        "submitted_at": request.get("submitted_at"),
                        "timestamp": time.time(),
                    }

            if event_payload is not None and command:
                append_event(event_payload)
                try:
                    menu_event = dispatch_live_menu_command(menu, command)
                    sync_result = sync_current_display(menu, menu_event)
                    write_status(
                        "HEADLESS_MENU_RUNNING",
                        buttons_available=buttons.available,
                        last_command=event_payload,
                        last_menu_event=(
                            menu_event.__dict__ if menu_event is not None else None
                        ),
                        display_mode=menu.display_mode,
                        selected_label=menu.selected_item.label,
                        last_display_sync=sync_result.get("sync_results", sync_result.get("sync_status")),
                    )
                except Exception as exc:
                    error_event: dict[str, object] = {
                        "type": "menu_action_error",
                        "command": command,
                        "error": str(exc),
                        "timestamp": time.time(),
                    }
                    try:
                        error_event["error_dig_sequence"] = run_standalone_error_sequence(
                            command,
                            str(exc),
                        )
                    except Exception as sequence_exc:
                        error_event["error_dig_sequence"] = {
                            "status": "failed_soft",
                            "error": str(sequence_exc),
                            "original_error_preserved": True,
                        }
                    append_event(error_event)
                    write_status(
                        "HEADLESS_MENU_ACTION_ERROR",
                        buttons_available=buttons.available,
                        command=command,
                        error=str(exc),
                        error_dig_sequence=error_event.get("error_dig_sequence"),
                    )
                continue

            idle_event = menu.check_idle_timeout()
            if idle_event is not None:
                sync_result = sync_current_display(menu, idle_event)
                write_status(
                    "HEADLESS_MENU_IDLE_FACE",
                    buttons_available=buttons.available,
                    display_mode=menu.display_mode,
                    last_menu_event=idle_event.__dict__,
                    last_display_sync=sync_result.get("sync_results", sync_result.get("sync_status")),
                )
    finally:
        buttons.close()
        write_status("HEADLESS_MENU_STOPPED", buttons_available=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())