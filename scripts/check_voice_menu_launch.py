#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from koalablue.menu_voice_launcher import build_menu_voice_manifest, parse_menu_voice_launch

STATUS_PATH = ROOT / "logs" / "menu_voice" / "voice_menu_launch_status.json"
MANIFEST_PATH = ROOT / "logs" / "menu_voice" / "voice_menu_launch_manifest.json"

SMOKE_PHRASES = {
    "open_main_submenu": "killerkoala open Bluetooth Tools",
    "run_submenu_leaf_label": "killerkoala run Eucalyptus Canopy Status",
    "run_submenu_leaf_command": "killerkoala run koala_bluez_status",
    "open_didgeridoo_submenu": "killerkoala open Didgeridoo",
    "run_system_item": "killerkoala run Level Status",
}


def main() -> int:
    failures: list[str] = []
    parsed = {}
    manifest = build_menu_voice_manifest()

    for name, phrase in SMOKE_PHRASES.items():
        match = parse_menu_voice_launch(phrase, require_wake_word=True)
        if match is None:
            failures.append(f"voice menu launch phrase did not match: {phrase}")
            parsed[name] = None
        else:
            parsed[name] = {
                "phrase": phrase,
                "label": match.label,
                "command": match.command,
                "is_submenu": match.is_submenu,
                "submenu": match.submenu,
                "verb": match.verb,
            }

    if manifest.get("entry_count", 0) < 10:
        failures.append("voice menu launch manifest has too few entries")

    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    payload = {
        "status": "VOICE_MENU_LAUNCH_READY" if not failures else "VOICE_MENU_LAUNCH_INCOMPLETE",
        "updated_at": time.time(),
        "syntax": manifest.get("syntax", []),
        "entry_count": manifest.get("entry_count", 0),
        "manifest_path": str(MANIFEST_PATH),
        "smoke": parsed,
        "failures": failures,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "manifest_path": str(MANIFEST_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
