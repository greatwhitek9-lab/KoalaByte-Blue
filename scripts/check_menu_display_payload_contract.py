#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_COMPANION = REPO_ROOT / "pi-companion"
if str(PI_COMPANION) not in sys.path:
    sys.path.insert(0, str(PI_COMPANION))

from koalablue.menu_display_sync import (  # noqa: E402
    _esp32_menu_payload,
    _heltec_face_payload,
    build_ai_face_payload,
    build_menu_sync_payload,
)
from koalablue.menu_ui import MenuSelectionScreen  # noqa: E402


def main() -> int:
    menu = MenuSelectionScreen()
    event = menu.reopen_menu("main_menu")
    menu_payload = build_menu_sync_payload(menu, event)
    visible_items = menu_payload.get("visible_items", [])
    esp32_payload = _esp32_menu_payload(menu_payload)
    heltec_menu_payload = _heltec_face_payload(menu_payload)

    idle_event = menu.show_ai_face(
        "idle",
        "KillerKoala idle — press K1/menu or double-tap to reopen",
        log_event_type="idle_timeout",
    )
    idle_payload = build_ai_face_payload(
        menu,
        idle_event,
        state="idle",
        message="KillerKoala idle — press K1/menu or double-tap to reopen",
    )
    heltec_idle_payload = _heltec_face_payload(idle_payload)

    checks = {
        "visible_rows_present": bool(visible_items),
        "visible_rows_have_labels": bool(visible_items)
        and all(str(item.get("label", "")).strip() for item in visible_items),
        "first_visible_label_is_eucalyptus": bool(visible_items)
        and str(visible_items[0].get("label")) == "Eucalyptus",
        "esp32_rows_have_labels": bool(esp32_payload.get("visible_items"))
        and all(
            str(item.get("label", "")).strip()
            for item in esp32_payload.get("visible_items", [])
        ),
        "heltec_menu_is_koalagotchi": heltec_menu_payload.get("display_mode")
        == "koalagotchi_action",
        "heltec_menu_is_not_text_menu": heltec_menu_payload.get("state")
        not in {"menu_highlight", "menu_select"},
        "heltec_idle_returns_to_mouth": "display_mode" not in heltec_idle_payload
        and heltec_idle_payload.get("state") == "idle",
    }
    ready = all(checks.values())
    result = {
        "ready": ready,
        "status": (
            "MENU_DISPLAY_PAYLOAD_CONTRACT_READY"
            if ready
            else "MENU_DISPLAY_PAYLOAD_CONTRACT_FAILED"
        ),
        "checks": checks,
        "first_visible_item": visible_items[0] if visible_items else None,
        "heltec_menu_payload": heltec_menu_payload,
        "heltec_idle_payload": heltec_idle_payload,
        "firmware_flash_required": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
