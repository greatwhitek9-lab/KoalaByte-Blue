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

from koalablue.killerkoala_face_bridge import (
    build_esp32_loading_eyes_payload,
    build_face_payload,
    build_heltec_loading_payload,
    emit_face,
    emit_loading_frame,
)

STATUS_PATH = ROOT / "logs" / "killerkoala_face" / "face_mouth_sync_status.json"
T114_FIRMWARE = ROOT / "firmware" / "t114-combined-safe" / "src" / "main.c"
T114_LOADING_RENDERER = ROOT / "firmware" / "t114-combined-safe" / "src" / "loading_display.c"
EYES_FIRMWARE = ROOT / "firmware" / "esp32-dualeye" / "src" / "main.cpp"

EXPECTED_STATES = ["wake", "listening", "thinking", "loading", "speaking", "action", "success", "error"]


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _status_payload(status: str, reason: str, *, emit_result: dict | None = None, loading_result: dict | None = None) -> dict:
    esp32_port = _env("KOALABYTE_ESP32_FACE_PORT") or _env("ESP32_PORT")
    heltec_port = _env("KOALABYTE_HELTEC_USB_PORT") or _env("KOALABYTE_HELTEC_FACE_PORT") or _env("HELTEC_PORT")
    payload = build_face_payload("wake", "killerkoala face sync check", duration_ms=1200)
    return {
        "status": status,
        "reason": reason,
        "updated_at": time.time(),
        "eyes_device": "ESP32-S3 DualEye",
        "loading_text_device": "Heltec T114 onboard ST7789 TFT",
        "shared_payload_type": payload.get("type"),
        "shared_transport": payload.get("transport"),
        "left_eye": payload.get("left_eye"),
        "right_eye": payload.get("right_eye"),
        "states": EXPECTED_STATES,
        "loading_split": {
            "heltec": "jungle_loading_banner",
            "esp32": "ai_eyes",
            "loading_text_on_esp32": False,
        },
        "esp32_port": esp32_port,
        "heltec_port": heltec_port,
        "emit_result": emit_result or {},
        "loading_emit_result": loading_result or {},
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

    heltec_loading = build_heltec_loading_payload("<< LOAD >>", "Readiness Monitors", duration_ms=1400)
    esp32_loading = build_esp32_loading_eyes_payload("Readiness Monitors", duration_ms=1400)
    if heltec_loading.get("message") != "<< LOAD >>":
        failures.append("Heltec loading payload lost the exact banner frame")
    if heltec_loading.get("display_mode") != "jungle_loading_banner":
        failures.append("Heltec loading payload is not routed to the jungle banner renderer")
    if len(json.dumps(heltec_loading, separators=(",", ":"))) >= 256:
        failures.append("Heltec loading payload exceeds the T114 USB command-line budget")
    if esp32_loading.get("display_mode") != "ai_eyes" or esp32_loading.get("preserve_eyes") is not True:
        failures.append("DualEye loading payload does not preserve the AI eyes")
    if esp32_loading.get("loading_text_on_eyes") is not False or esp32_loading.get("message"):
        failures.append("DualEye loading payload must not draw the loading banner over the eyes")

    failures.extend(
        _file_contains(
            T114_FIRMWARE,
            [
                "killerkoala_face",
                "killerkoala_tft_ack",
                "heltec_mouth_status",
                "jungle_loading_banner",
                "render_loading_banner",
            ],
        )
    )
    failures.extend(
        _file_contains(
            T114_LOADING_RENDERER,
            [
                "DT_CHOSEN(zephyr_display)",
                "PIXEL_FORMAT_RGB_565",
                "ST7789",
                "draw_jungle_frame",
            ],
        )
    )
    failures.extend(
        _file_contains(
            EYES_FIRMWARE,
            ["killerkoala_face", "esp32-dualeye", "left_eye", "right_eye", "killerkoala_eye_ack"],
        )
    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ESP32-S3 eyes and Heltec T114 loading-display face-state sync")
    parser.add_argument("--emit-test", action="store_true", help="Send a short shared wake-state payload to both configured serial targets")
    parser.add_argument("--emit-loading-test", action="store_true", help="Send one split loading frame: text to T114 and eyes-only to DualEye")
    parser.add_argument("--strict-ports", action="store_true", help="Fail if configured serial writes do not succeed during emit tests")
    args = parser.parse_args()

    failures = validate_protocol()
    emit_result: dict | None = None
    loading_result: dict | None = None
    if args.emit_test:
        emit_result = emit_face("wake", "eyes and T114 synced", duration_ms=1400)
        if args.strict_ports:
            if not emit_result.get("wrote_esp32"):
                failures.append("strict sync: ESP32-S3 eyes did not accept face payload")
            if not emit_result.get("wrote_heltec"):
                failures.append("strict sync: Heltec T114 did not accept face payload")
    if args.emit_loading_test:
        loading_result = emit_loading_frame("<< LOAD >>", "loading sync test", duration_ms=1400)
        if args.strict_ports:
            if not loading_result.get("wrote_esp32"):
                failures.append("strict loading sync: ESP32-S3 eyes did not accept eyes-only payload")
            if not loading_result.get("wrote_heltec"):
                failures.append("strict loading sync: Heltec T114 did not accept banner payload")

    if failures:
        _write(_status_payload("FACE_MOUTH_SYNC_FAILED", "; ".join(failures), emit_result=emit_result, loading_result=loading_result))
        return 1
    _write(
        _status_payload(
            "FACE_MOUTH_SYNC_READY",
            "T114 renders loading text while ESP32-S3 keeps the KillerKoala AI eyes active",
            emit_result=emit_result,
            loading_result=loading_result,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
