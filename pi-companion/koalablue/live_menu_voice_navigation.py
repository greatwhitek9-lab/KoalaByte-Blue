from __future__ import annotations

from typing import Any, Callable, Optional

from .hdmi_display_state import submit_menu_command


def live_menu_command_for_match(match: Any) -> Optional[str]:
    """Translate a parsed voice submenu target into the live menu command bus."""

    if not bool(getattr(match, "is_submenu", False)):
        return None
    command = str(getattr(match, "command", "") or "").strip()
    if command == "submenu:main":
        return "main_menu"
    if command.startswith("submenu:"):
        return command
    return None


def install_live_menu_voice_navigation() -> Callable[..., Any]:
    """Route voice submenu navigation through the running headless menu service.

    The voice launcher historically constructed a separate temporary menu object.
    That made a voice request look successful in its artifact while the live
    K1-K6 menu state never changed. This wrapper submits submenu navigation to the
    same command queue consumed by ``koalabyte-menu.service`` before retaining the
    existing launcher result/TTS behavior.
    """

    from . import menu_voice_launcher

    original = menu_voice_launcher.execute_menu_voice_launch
    if getattr(original, "_koalabyte_live_menu_voice_navigation", False):
        return original

    def execute_menu_voice_launch(match: Any, *args: Any, **kwargs: Any):
        live_command = live_menu_command_for_match(match)
        submission = None
        if live_command:
            submission = submit_menu_command(
                live_command,
                source="killerkoala-voice",
            )

        result = original(match, *args, **kwargs)
        if submission is not None:
            try:
                details = getattr(result, "details", None)
                if isinstance(details, dict):
                    details["live_menu_navigation"] = {
                        "command": live_command,
                        "submitted": True,
                        "submission": dict(submission),
                    }
            except Exception:
                pass
        return result

    execute_menu_voice_launch._koalabyte_live_menu_voice_navigation = True  # type: ignore[attr-defined]
    menu_voice_launcher.execute_menu_voice_launch = execute_menu_voice_launch
    return execute_menu_voice_launch


__all__ = [
    "install_live_menu_voice_navigation",
    "live_menu_command_for_match",
]
