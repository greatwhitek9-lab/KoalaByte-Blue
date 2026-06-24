#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_COMPANION = ROOT / "pi-companion"
if str(PI_COMPANION) not in sys.path:
    sys.path.insert(0, str(PI_COMPANION))

from koalablue.killerkoala_face_bridge import build_face_payload, emit_face

STATUS_PATH = ROOT / "logs" / "killerkoala_face" / "face_mouth_sync_status.json"
MOUTH_FIRMWARE = ROOT / "firmware" / "heltec-mouth" / "src" / "main.cpp"
EYES_FIRMWARE = ROOT / "firmware" / "esp32-dualeye" / "src" / "main.cpp"

EXPECTED_STATES = ["wake", "listening", "thinking", "speaking", "action", "success", "error"]


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _status_payload(status: str, reason: str, *, emit_result: dict | None = None) -> dict:
    esp32_port = _env("KOALABYTE_ESP32_FACE_PORT") or _env("ESP32_PORT")
    heltec_port = _env("KOALABYTE_HELTEC_USB_PORT") or _env("KOALABYTE_HELTEC_FACE_PORT") or _env("HELTEC_PORT")
    payload = build_face_payload("wake", "killerkoala face sync check", duration_ms=1200)
    return {
        "status": status,
        "reason": reason,
        "updated_at": time.time(),
        "eyes_device": "ESP32-S3 DualEye",
        "mouth_device": "Heltec T114 color-mouth firmware",
        "shared_payload_type": payload.get("type"),
        "shared_transport": payload.get("transport"),
        "left_eye": payload.get("left_eye"),
        "right_eye": payload.get("right_eye"),
        "states": EXPECTED_STATES,
        "esp32_port": esp32_port,
        "heltec_port": heltec_port,
        "emit_result": emit_result or {},
    }


def _write(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


def _file_contains(path: Path, needles: list[str]) -> list[str]:
    if not path.exists():
        return [f"missing file: {path.relative_to(ROOT)}"]
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [f"{path.relative_to(ROOT)} missing {needle}" for needle in needles if needle not in text]


def validate_protocol() -> list[str]:
    failures: list[str] = []
    for state in EXPECTED_STATES:
        payload = build_face_payload(state, f"sync {state}", duration_ms=800)
        if payload.get("type") != "killerkoala_face":
            failures.append(f"payload type mismatch for {state}")
        if payload.get("state") != state:
            failures.append(f"payload state mismatch for {state}")
        if payload.get("left_eye") != "#A54BFF":
            failures.append("left eye UV color changed")
        if payload.get("right_eye") != "#32FF71":
            failures.append("right eye green color changed")
        if payload.get("transport") != "usb-cdc":
            failures.append("face transport must stay usb-cdc")
    failures.extend(_file_contains(MOUTH_FIRMWARE, ["killerkoala_face", "ai_face", "killerkoala_tft_ack", "heltec_mouth_status"]))
    failures.extend(_file_contains(EYES_FIRMWARE, ["killerkoala_face", "esp32-dualeye", "left_eye", "right_eye", "killerkoala_eye_ack"]))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ESP32-S3 eyes and Heltec T114 mouth face-state sync")
    parser.add_argument("--emit-test", action="store_true", help="Send a short test face payload to both configured serial targets")
    parser.add_argument("--strict-ports", action="store_true", help="Fail if either ESP32 or Heltec write does not succeed during --emit-test")
    args = parser.parse_args()

    failures = validate_protocol()
    emit_result: dict | None = None
    if args.emit_test:
        emit_result = emit_face("wake", "eyes and mouth synced", duration_ms=1400)
        if args.strict_ports:
            if not emit_result.get("wrote_esp32"):
                failures.append("strict sync: ESP32-S3 eyes did not accept face payload")
            if not emit_result.get("wrote_heltec"):
                failures.append("strict sync: Heltec mouth did not accept face payload")

    if failures:
        _write(_status_payload("FACE_MOUTH_SYNC_FAILED", "; ".join(failures), emit_result=emit_result))
        return 1
    _write(_status_payload("FACE_MOUTH_SYNC_READY", "ESP32-S3 eyes and Heltec mouth share the KillerKoala face-state protocol", emit_result=emit_result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
