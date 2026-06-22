#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

REQUIRED_FILES = [
    "README.md",
    "firmware/esp32-dualeye/include/config.h",
    "firmware/esp32-dualeye/src/main.cpp",
    "firmware/esp32-dualeye/src/koalagotchi_mode_screens.cpp",
    "firmware/esp32-dualeye/src/killerkoala_ai_face.h",
    "firmware/esp32-dualeye/src/killerkoala_ai_face.cpp",
    "firmware/heltec-mouth/platformio.ini",
    "firmware/heltec-mouth/include/config.h",
    "firmware/heltec-mouth/src/main.cpp",
    "pi-companion/config.default.json",
    "pi-companion/koalablue/menu_catalog.py",
    "pi-companion/koalablue/killerkoala_face_bridge.py",
    "pi-companion/koalablue/killerkoala_voice_face_control.py",
    "scripts/run_menu_screen.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_killerkoala_face_demo.py",
    "scripts/flash_heltec_mouth.sh",
]

REQUIRED_TEXT = {
    "firmware/esp32-dualeye/src/main.cpp": ["killerkoala_ai_face", "showKillerKoalaAiFace", "isKillerKoalaAiFaceActive"],
    "firmware/esp32-dualeye/src/killerkoala_ai_face.cpp": ["KILLERKOALA", "KOALA AI COMPANION", "koalaEar"],
    "firmware/heltec-mouth/src/main.cpp": ["drawSnout", "killerkoala_face", "suppressed_for_app"],
    "pi-companion/koalablue/killerkoala_face_bridge.py": ["KOALABYTE_ESP32_FACE_PORT", "KOALABYTE_HELTEC_FACE_PORT", "KOALAGOTCHI_DISPLAY_COMMANDS"],
    "scripts/run_menu_screen.py": ["emit_selected_action_face", "run_anteater_action", "anteater"],
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        if not (REPO_ROOT / rel).exists():
            failures.append(f"missing required file: {rel}")
    for rel, needles in REQUIRED_TEXT.items():
        text = read_text(REPO_ROOT / rel)
        for needle in needles:
            if needle not in text:
                failures.append(f"{rel} missing expected text: {needle}")
    try:
        json.loads((REPO_ROOT / "pi-companion" / "config.default.json").read_text(encoding="utf-8"))
        from koalablue.menu_catalog import menu_labels
        if not menu_labels():
            failures.append("menu catalog has no labels")
    except Exception as exc:
        failures.append(f"basic import/config check failed: {exc}")
    if failures:
        print("KoalaByte Blue repo readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("KoalaByte Blue repo readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
