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
    build_koalagotchi_status_payload,
    build_speech_payload,
    emit_face,
    emit_loading_frame,
    select_koalagotchi_expression,
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
            "heltec": "koalagotchi_action",
            "esp32": "action_status",
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
    if heltec_loading.get("state") != "koalagotchi_action":
        failures.append("Heltec action payload is not routed to Koalagotchi")
    if heltec_loading.get("display_mode") != "koalagotchi_action":
        failures.append("Heltec action payload does not select the Koalagotchi renderer")
    if heltec_loading.get("frame_index") != 3:
        failures.append("Heltec Koalagotchi payload lost the action frame")
    if len(json.dumps(heltec_loading, separators=(",", ":"))) >= 256:
        failures.append("Heltec loading payload exceeds the T114 USB command-line budget")
    if esp32_loading.get("type") != "menu_sync":
        failures.append("DualEye executing-action payload is not menu_sync")
    if esp32_loading.get("display_mode") != "action_status":
        failures.append("DualEye executing-action payload does not select action status")
    if esp32_loading.get("selected_label") != "Readiness Monitors":
        failures.append("DualEye executing-action payload lost the action name")
    if esp32_loading.get("loading_text_on_eyes") is not False or esp32_loading.get("message"):
        failures.append("DualEye loading payload must not draw the loading banner over the eyes")

    expression_cases = [
        (92, "happy and content", "smile"),
        (76, "eating eucalyptus Bluetooth leaves", "bite"),
        (18, "cranky boomerang toss", "snarl"),
        (70, "patrolling the gum branch", "sideways_grin"),
    ]
    for health, mood, expected_expression in expression_cases:
        expression = select_koalagotchi_expression(health, mood)
        if expression != expected_expression:
            failures.append(f"health/mood mapping {health}/{mood!r} produced {expression}, expected {expected_expression}")
        status_payload = build_koalagotchi_status_payload(health, mood)
        if status_payload.get("type") != "koalagotchi_status":
            failures.append("Koalagotchi mouth payload type changed")
        if status_payload.get("expression") != expected_expression:
            failures.append(f"Koalagotchi payload lost {expected_expression} expression")
        if len(json.dumps(status_payload, separators=(",", ":"))) >= 256:
            failures.append("Koalagotchi health/mood payload exceeds the T114 USB command-line budget")

    speech_start = build_speech_payload(True, "KillerKoala is speaking locally", "local-ai")
    speech_stop = build_speech_payload(False, channel="pi-ai")
    if speech_start.get("type") != "killerkoala_speech" or speech_start.get("active") is not True:
        failures.append("AI speech start does not activate the T114 speaking mouth")
    if speech_stop.get("active") is not False or speech_stop.get("message"):
        failures.append("AI speech stop does not settle the T114 speaking mouth")
    if len(json.dumps(speech_start, separators=(",", ":"))) >= 256:
        failures.append("AI speech payload exceeds the T114 USB command-line budget")

    failures.extend(
        _file_contains(
            T114_FIRMWARE,
            [
                "killerkoala_face",
                "killerkoala_tft_ack",
                "heltec_mouth_status",
                "jungle_loading_banner",
                "render_loading_banner",
                "render_killerkoala_mouth",
                "render_menu_status",
                "KOALA_BOOT_SPLASH_MS",
                'strcmp(current_display_mode(), "killerkoala_mouth") == 0',
                "koalagotchi_status",
                "killerkoala_speech",
                "handle_speech_command",
                "expression_from_koalagotchi",
                "idle_sequences",
                "speaking_sequence",
                "eased_mouth_blend",
                "KOALA_IDLE_TRANSITION_STEPS",
                "KOALA_SPEECH_TRANSITION_STEPS",
            ],
        )
    )
    failures.extend(
        _file_contains(
            T114_LOADING_RENDERER,
            [
                "DT_CHOSEN(zephyr_display)",
                "PIXEL_FORMAT_RGB_565",
                "TFT_WIDTH",
                "draw_jungle_frame",
                "draw_killerkoala_mouth_frame",
                "KILLERKOALA_MOUTH_TEXT_FREE",
                "KILLERKOALA_CYBER_MOUTH_FRAME_BYTES 64800",
                "killerkoala_cyber_mouth_smile_rgb565_be",
                "killerkoala_cyber_mouth_happy_rgb565_be",
                "killerkoala_cyber_mouth_bite_rgb565_be",
                "killerkoala_cyber_mouth_snarl_rgb565_be",
                "killerkoala_cyber_mouth_sideways_grin_rgb565_be",
                "blend_rgb565_be",
                "blend_amount",
                "draw_koalagotchi_action_frame",
                "render_killerkoala_boot_splash",
                "render_koalagotchi_action",
                "render_menu_status",
            ],
        )
    )
    renderer_text = T114_LOADING_RENDERER.read_text(encoding="utf-8", errors="ignore")
    mouth_start = renderer_text.find("static void draw_killerkoala_mouth_frame")
    mouth_end = renderer_text.find("static void draw_koalagotchi_action_frame", mouth_start)
    if mouth_start < 0 or mouth_end < 0:
        failures.append("T114 text-free mouth renderer boundaries are missing")
    elif "draw_centered_text_at" in renderer_text[mouth_start:mouth_end]:
        failures.append("T114 mouth renderer must not draw IDLE, KILLERKOALA, or other words")
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
    parser.add_argument("--emit-loading-test", action="store_true", help="Send one action frame: Koalagotchi to T114 and action label to DualEye")
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
                failures.append("strict action sync: ESP32-S3 DualEye did not accept the action label")
            if not loading_result.get("wrote_heltec"):
                failures.append("strict action sync: Heltec T114 did not accept Koalagotchi")

    if failures:
        _write(_status_payload("FACE_MOUTH_SYNC_FAILED", "; ".join(failures), emit_result=emit_result, loading_result=loading_result))
        return 1
    _write(
        _status_payload(
            "FACE_MOUTH_SYNC_READY",
            "T114 artwork boot splash transitions to a text-free cyberpunk koala mouth with eased RGB565 pose interpolation, irregular multi-expression idle choreography, and speech start/stop lip movement for Pi/local AI audio; T114 still plays Koalagotchi during actions while ESP32-S3 DualEye displays the executing action name",
            emit_result=emit_result,
            loading_result=loading_result,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
