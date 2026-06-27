#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATUS_PATH = ROOT / "logs" / "one_shot" / "menu_display_sync_status.json"


def _failures_from_payload(payload: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if payload.get("type") != "menu_sync":
        failures.append("menu payload type must be menu_sync")
    controls = payload.get("controls", {})
    if not isinstance(controls, dict):
        failures.append("menu payload controls must be a dict")
    else:
        select_controls = set(controls.get("select", [])) if isinstance(controls.get("select"), list) else set()
        if "B3" not in select_controls:
            failures.append("B3/select must be advertised as a select control")
        if "touch_long_press" not in select_controls:
            failures.append("touch_long_press must be advertised as a select control")
        reopen_controls = set(controls.get("reopen_menu", [])) if isinstance(controls.get("reopen_menu"), list) else set()
        if "B1" not in reopen_controls:
            failures.append("B1/menu must be advertised as a menu reopen control")
        if "touch_double_tap" not in reopen_controls:
            failures.append("touch_double_tap must be advertised as a menu reopen control")
    if "B3/select or touchscreen long-press" not in str(payload.get("execute_hint", "")):
        failures.append("execute hint must mention B3/select or touchscreen long-press")
    if "30 seconds idle" not in str(payload.get("idle_face_rule", "")):
        failures.append("idle face rule must mention 30 seconds idle")
    displays = set(payload.get("synced_displays", [])) if isinstance(payload.get("synced_displays"), list) else set()
    if "heltec-t114" not in displays or "esp32-s3-dualeye" not in displays:
        failures.append("sync payload must target both Heltec T114 and ESP32-S3 DualEye")
    return failures


def main() -> int:
    os.environ.setdefault("KOALABYTE_MENU_SYNC", "0")

    from koalablue.menu_display_sync import build_ai_face_payload, build_menu_sync_payload, sync_ai_face_display, sync_menu_state
    from koalblue.menu_ui import MenuSelectionScreen

    # The module is koalablue; keep this import fallback impossible at runtime, but
    # leave an explicit failure message if a bad package alias ever appears again.
    raise RuntimeError("unexpected koalblue import alias")


if __name__ == "__main__":
    raise SystemExit(main())
