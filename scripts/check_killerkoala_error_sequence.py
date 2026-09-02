#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

# Keep readiness deterministic and offline. The runtime defaults to TinyLlama,
# while this check validates the phrase fallback, lifecycle, and anti-repeat path.
os.environ.setdefault("KILLERKOALA_LLM_MODE", "off")
os.environ.setdefault("KOALABYTE_ERROR_ALARM_SECONDS", "0.6")

from koalablue.esp32_dualeye_error_dig_bridge import (  # noqa: E402
    ESP32DualEyeVoiceBridge,
)

STATUS_PATH = ROOT / "logs" / "killerkoala" / "error_sequence_readiness.json"


def require_marker(path: Path, marker: str, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"missing error-sequence file: {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    if marker not in text:
        failures.append(f"{path.relative_to(ROOT)} missing marker: {marker}")


def main() -> int:
    failures: list[str] = []
    esp32_packets: list[dict[str, Any]] = []
    heltec_packets: list[dict[str, Any]] = []
    spoken: list[tuple[str, str]] = []

    with tempfile.TemporaryDirectory(prefix="koalabyte-error-check-") as temp:
        temp_path = Path(temp)
        bridge = ESP32DualEyeVoiceBridge(
            port="/dev/null",
            status_path=temp_path / "mic.json",
            events_path=temp_path / "events.jsonl",
            xp_path=temp_path / "xp_state.json",
        )
        bridge._write_json = lambda payload, **_: esp32_packets.append(dict(payload))  # type: ignore[method-assign]
        bridge._write_heltec = lambda payload: heltec_packets.append(dict(payload))  # type: ignore[method-assign]
        bridge._play_response = lambda text, channel: spoken.append((text, channel))  # type: ignore[method-assign]

        bridge._start_error_sequence("BLE fallback", "controller startup fault")
        first_dig = bridge._pending_error_dig
        if not bridge._active_error:
            failures.append("first error did not activate the alarm lifecycle")
        if not first_dig:
            failures.append("first error did not select a KillerKoala dig")
        if not any(packet.get("state") == "alarmed" for packet in esp32_packets):
            failures.append("DualEye alarmed packet was not emitted")
        if not any(packet.get("state") == "alarmed" for packet in heltec_packets):
            failures.append("T114 alarmed Koalagotchi packet was not emitted")
        alarm_packet = next(
            (packet for packet in esp32_packets if packet.get("state") == "alarmed"),
            {},
        )
        if alarm_packet.get("alarm_colors") != ["#A54BFF", "#32FF71"]:
            failures.append("DualEye alarm packet does not declare purple/green colors")
        if alarm_packet.get("alarm_flash_ms") != 180:
            failures.append("DualEye alarm packet does not use the 180ms flash cadence")

        bridge._error_alarm_until = time.time() - 1
        bridge._service_error_sequence()
        if bridge._active_error:
            failures.append("first alarm did not clear after its sequence deadline")
        if not any(packet.get("state") == "error_clear" for packet in esp32_packets):
            failures.append("DualEye error_clear packet was not emitted")
        if not any(packet.get("state") == "error_clear" for packet in heltec_packets):
            failures.append("T114 error_clear packet was not emitted")
        if not spoken or spoken[-1] != (first_dig, "pi-error-dig"):
            failures.append("Pi did not speak the selected dig after alarm completion")

        bridge._start_error_sequence("Music player", "stream unavailable error")
        second_dig = bridge._pending_error_dig
        if second_dig == first_dig:
            failures.append("consecutive error digs repeated")
        bridge._error_alarm_until = time.time() - 1
        bridge._service_error_sequence()
        if len(spoken) != 2:
            failures.append("second completed alarm did not produce exactly one dig")

    require_marker(
        ROOT / "pi-companion/koalablue/killerkoala_error_dig.py",
        "generate_error_dig",
        failures,
    )
    require_marker(
        ROOT / "pi-companion/koalablue/esp32_dualeye_error_dig_bridge.py",
        "raw exception",
        failures,
    )
    require_marker(
        ROOT / "scripts/run_esp32_dualeye_voice_bridge.py",
        "esp32_dualeye_observed_bridge",
        failures,
    )
    require_marker(
        ROOT / "pi-companion/koalablue/esp32_dualeye_observed_bridge.py",
        "esp32_dualeye_sphinx_bridge",
        failures,
    )
    require_marker(
        ROOT / "pi-companion/koalablue/esp32_dualeye_sphinx_bridge.py",
        "esp32_dualeye_error_dig_bridge",
        failures,
    )
    require_marker(
        ROOT / "firmware/esp32-dualeye/scripts/patch_alarm_background.py",
        "flashing purple/green DualEye alarm lifecycle",
        failures,
    )
    require_marker(
        ROOT / "firmware/esp32-dualeye/platformio.ini",
        "patch_alarm_background.py",
        failures,
    )
    require_marker(
        ROOT / "firmware/t114-combined-safe/src/koalagotchi_lifecycle_wrapper.c",
        "overlay_alarm_background",
        failures,
    )
    require_marker(
        ROOT / "firmware/t114-combined-safe/src/koalagotchi_lifecycle_wrapper.c",
        "overlay_alerted",
        failures,
    )
    require_marker(
        ROOT / "firmware/t114-combined-safe/src/koalagotchi_lifecycle_wrapper.c",
        "error_clear",
        failures,
    )

    payload = {
        "status": "KILLERKOALA_ERROR_SEQUENCE_READY" if not failures else "KILLERKOALA_ERROR_SEQUENCE_INCOMPLETE",
        "sequence": [
            "error_detected",
            "dualeye_alert_eyes_and_purple_green_background",
            "heltec_alarmed_koalagotchi_and_purple_green_background",
            "explicit_error_clear_to_mouth",
            "pi_generated_australian_voice_nonrepeating_dig",
            "idle_mouth_and_eyes",
        ],
        "first_dig": first_dig,
        "second_dig": second_dig,
        "esp32_packet_count": len(esp32_packets),
        "heltec_packet_count": len(heltec_packets),
        "spoken": spoken,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
