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

from koalablue.control_mode import gpio_buttons_enabled, load_control_mode, write_control_mode

STATUS_PATH = ROOT / "logs" / "control" / "control_mode_fallback_readiness.json"


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="koalabyte-control-mode-") as tmp:
        previous_path = os.environ.get("KOALABYTE_CONTROL_MODE_PATH")
        previous_mode = os.environ.get("KOALABYTE_CONTROL_MODE")
        os.environ["KOALABYTE_CONTROL_MODE_PATH"] = str(Path(tmp) / "control_mode.json")
        os.environ.pop("KOALABYTE_CONTROL_MODE", None)
        try:
            fallback = write_control_mode(
                "touch_speech_only",
                reason="readiness test",
                source="check_control_mode_fallback",
                buttons_available=False,
            )
            loaded = load_control_mode()
            if loaded.get("mode") != "touch_speech_only":
                failures.append(f"persisted fallback mode mismatch: {loaded}")
            if gpio_buttons_enabled():
                failures.append("GPIO buttons remained enabled in touch_speech_only mode")
            for key in ["touch_enabled", "speech_enabled", "keyboard_enabled"]:
                if fallback.get(key) is not True:
                    failures.append(f"fallback did not keep {key}=true")

            restored = write_control_mode(
                "full_controls",
                reason="readiness recovery test",
                source="check_control_mode_fallback",
                buttons_available=True,
            )
            if restored.get("gpio_buttons_enabled") is not True or not gpio_buttons_enabled():
                failures.append("full_controls recovery did not re-enable GPIO buttons")
        finally:
            if previous_path is None:
                os.environ.pop("KOALABYTE_CONTROL_MODE_PATH", None)
            else:
                os.environ["KOALABYTE_CONTROL_MODE_PATH"] = previous_path
            if previous_mode is None:
                os.environ.pop("KOALABYTE_CONTROL_MODE", None)
            else:
                os.environ["KOALABYTE_CONTROL_MODE"] = previous_mode

    required_markers = {
        ROOT / "scripts" / "setup_gpio_buttons.py": [
            "GPIO_BUTTONS_UNAVAILABLE_TOUCH_SPEECH_ONLY",
            "installer_continues",
            "STRICT_GPIO_BUTTONS",
            "run_probe",
        ],
        ROOT / "scripts" / "koalabyte_blue_boot.sh": [
            "KOALABYTE_CONTROL_MODE",
            "touch_speech_only",
            "Touchscreen, KillerKoala speech control",
        ],
        ROOT / "pi-companion" / "koalablue" / "gpio_buttons.py": [
            "gpio_buttons_enabled",
            "_record_touch_speech_fallback",
            "touch_speech_only",
        ],
    }
    for path, markers in required_markers.items():
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        if not text:
            failures.append(f"missing fallback file: {path.relative_to(ROOT)}")
            continue
        for marker in markers:
            if marker not in text:
                failures.append(f"{path.relative_to(ROOT)} missing fallback marker: {marker}")

    payload = {
        "status": "TOUCH_SPEECH_FALLBACK_READY" if not failures else "TOUCH_SPEECH_FALLBACK_INCOMPLETE",
        "fallback_mode": "touch_speech_only",
        "installer_continues_by_default": True,
        "strict_override": "STRICT_GPIO_BUTTONS=1",
        "touch_enabled": True,
        "speech_enabled": True,
        "keyboard_enabled": True,
        "gpio_buttons_enabled_in_fallback": False,
        "updated_at": time.time(),
        "failures": failures,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
