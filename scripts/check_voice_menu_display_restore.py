#!/usr/bin/env python3
from __future__ import annotations

import json

from koalablue.esp32_dualeye_voice_bridge import ESP32DualEyeVoiceBridge
from koalablue.killerkoala_voice_display_policy import (
    install_voice_menu_display_restore,
)


def _preview(phrase: str) -> tuple[dict, list[dict], list[tuple]]:
    install_voice_menu_display_restore(ESP32DualEyeVoiceBridge)
    bridge = ESP32DualEyeVoiceBridge(port="/dev/null")
    writes: list[dict] = []
    faces: list[tuple] = []
    bridge._write_json = lambda payload, **_kwargs: writes.append(dict(payload))  # type: ignore[method-assign]
    bridge._fanout_face = lambda *args, **kwargs: faces.append((args, kwargs))  # type: ignore[method-assign]
    payload = bridge._menu_preview(phrase)
    assert payload is not None, phrase
    return payload, writes, faces


def main() -> int:
    menu_payload, menu_writes, menu_faces = _preview(
        "killer koala kruisin prompt status"
    )
    direct_payload, direct_writes, direct_faces = _preview(
        "killer koala bluez status"
    )

    checks = {
        "spoken_wake_menu_preview": menu_payload["selected_command"]
        == "kruisin_prompt_status",
        "menu_preview_uses_highlight": menu_payload["event_type"] == "highlight",
        "menu_preview_visible_intent": menu_payload["display_intent"]
        == "voice_menu_preview",
        "menu_preview_written_once": len(menu_writes) == 1,
        "menu_preview_does_not_force_action_face": not menu_faces,
        "direct_module_preview": direct_payload["selected_command"]
        == "koala_bluez_status",
        "direct_preview_uses_highlight": direct_payload["event_type"] == "highlight",
        "direct_preview_written_once": len(direct_writes) == 1,
        "direct_preview_does_not_force_action_face": not direct_faces,
    }
    failures = [name for name, passed in checks.items() if not passed]
    payload = {
        "ready": not failures,
        "status": "VOICE_MENU_DISPLAY_RESTORED" if not failures else "VOICE_MENU_DISPLAY_RESTORE_FAILED",
        "checks": checks,
        "failures": failures,
        "menu_preview": menu_payload,
        "direct_module_preview": direct_payload,
        "hardware_accessed": False,
        "firmware_flash_required": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
