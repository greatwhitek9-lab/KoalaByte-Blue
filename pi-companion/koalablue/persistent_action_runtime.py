from __future__ import annotations

from typing import Any, Callable

from .persistent_action_state import (
    active_actions,
    apply_lifecycle_transition,
    lifecycle_intent,
)


def _install_runner_lifecycle() -> Callable[..., Any]:
    """Persist lifecycle state for every menu/voice action execution."""

    from . import menu_action_runner

    original = menu_action_runner.run_automated_menu_action
    if getattr(original, "_koalabyte_persistent_action_runtime", False):
        return original

    def run_automated_menu_action(command: str, label: str = "", group: str = ""):
        result = original(command, label, group)
        transition = apply_lifecycle_transition(
            command,
            label,
            result,
            source="menu_or_voice",
        )
        if transition is not None and isinstance(result, dict):
            result["persistent_action"] = transition
            result["persistent_action_active"] = bool(transition.get("active", False))
            result["persistent_action_key"] = str(transition.get("key") or "")
        return result

    run_automated_menu_action._koalabyte_persistent_action_runtime = True  # type: ignore[attr-defined]
    menu_action_runner.run_automated_menu_action = run_automated_menu_action
    return run_automated_menu_action


def _install_menu_lifecycle() -> type[Any]:
    """Keep the selected action face latched for successful START/ON commands."""

    from .menu_ui import MenuSelectionScreen

    if getattr(MenuSelectionScreen, "_koalabyte_persistent_action_runtime", False):
        return MenuSelectionScreen

    def persistent_run_selected_handler(self: Any, item: Any, select_event_type: str):
        event = self._event(select_event_type, item.command)
        handler = self._handlers.get(item.command)
        intent = lifecycle_intent(item.command, item.label)
        self.show_ai_face(
            "action_running",
            f"Running {item.label}",
            log_event_type="action_running",
        )
        result: Any = None
        try:
            if handler:
                result = handler(item)
                # Custom handlers bypass menu_action_runner, so persist their
                # explicit lifecycle transition here after a successful return.
                transition = apply_lifecycle_transition(
                    item.command,
                    item.label,
                    result,
                    source="menu_handler",
                )
            else:
                from .menu_action_runner import run_automated_menu_action

                result = run_automated_menu_action(item.command, item.label, item.group)
                transition = (
                    result.get("persistent_action")
                    if isinstance(result, dict)
                    else None
                )
        except Exception:
            self.show_ai_face(
                "error",
                f"{item.label} hit a snag",
                log_event_type="action_error",
            )
            raise

        if intent in {"start", "restart"} and transition and bool(transition.get("active", False)):
            self.show_ai_face(
                "action_active",
                f"{item.label} active — use its Stop/Off command to end it",
                log_event_type="action_active",
            )
        elif intent == "stop" and transition and not bool(transition.get("active", False)):
            self.show_ai_face(
                "action_stopped",
                f"{item.label} stopped",
                log_event_type="action_stopped",
            )
        else:
            self.show_ai_face(
                "action_complete",
                f"{item.label} complete",
                log_event_type="action_complete",
            )
        return event

    MenuSelectionScreen._run_selected_handler = persistent_run_selected_handler
    MenuSelectionScreen._koalabyte_persistent_action_runtime = True
    return MenuSelectionScreen


def _expand_voice_persistent_commands() -> set[str]:
    """Make every explicit lifecycle START/ON command persistent in voice UI."""

    from .killerkoala_face_bridge import KOALAGOTCHI_DISPLAY_COMMANDS
    from .menu_catalog import all_menu_entries

    for row in all_menu_entries():
        command = str(row.get("command") or "").strip()
        label = str(row.get("label") or "").strip()
        if lifecycle_intent(command, label) in {"start", "restart"}:
            KOALAGOTCHI_DISPLAY_COMMANDS.add(command)
    return KOALAGOTCHI_DISPLAY_COMMANDS


def install_persistent_action_runtime() -> dict[str, Any]:
    """Install persistent START/STOP semantics across menu and voice execution."""

    _install_runner_lifecycle()
    _install_menu_lifecycle()
    commands = _expand_voice_persistent_commands()
    return {
        "status": "PERSISTENT_ACTION_RUNTIME_INSTALLED",
        "voice_persistent_commands": sorted(commands),
        "active_actions": active_actions(),
    }


__all__ = ["install_persistent_action_runtime"]
