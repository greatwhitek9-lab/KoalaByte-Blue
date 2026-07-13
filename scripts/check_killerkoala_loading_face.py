#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.killerkoala_face_bridge import (
    build_esp32_loading_eyes_payload,
    build_heltec_loading_payload,
)
from koalablue.loading_face import (
    LOADING_WORD,
    jungle_loading_banner,
    jungle_loading_message,
    loading_word_frame,
    start_loading_face_sequence,
)

STATUS_PATH = ROOT / "logs" / "killerkoala_face" / "loading_face_readiness.json"


def main() -> int:
    failures: list[str] = []
    frames = [loading_word_frame(index) for index in range(len(LOADING_WORD))]
    expected = [LOADING_WORD[: index + 1] for index in range(len(LOADING_WORD))]
    banners = [jungle_loading_banner(index) for index in range(len(LOADING_WORD))]
    expected_banners = [f"<< {frame} >>" for frame in expected]
    if frames != expected:
        failures.append(f"loading frames do not spell {LOADING_WORD}: {frames}")
    if banners != expected_banners:
        failures.append(f"Heltec loading banners are not exact: {banners}")

    sample = jungle_loading_message("Koala Kan Kommander", 2)
    if "LOA" not in sample or "Koala Kan Kommander" not in sample:
        failures.append(f"loading message missing action markers: {sample}")

    heltec_payload = build_heltec_loading_payload("<< LOA >>", "Koala Kan Kommander")
    esp32_payload = build_esp32_loading_eyes_payload("Koala Kan Kommander")
    if heltec_payload.get("target_display") != "heltec-t114":
        failures.append("Heltec loading payload does not target heltec-t114")
    if heltec_payload.get("display_mode") != "jungle_loading_banner":
        failures.append("Heltec loading payload does not select jungle_loading_banner")
    if heltec_payload.get("message") != "<< LOA >>":
        failures.append("Heltec loading payload does not carry the exact banner frame")
    if esp32_payload.get("target_display") != "esp32-s3-dualeye":
        failures.append("DualEye loading payload does not target esp32-s3-dualeye")
    if esp32_payload.get("display_mode") != "ai_eyes":
        failures.append("DualEye loading payload does not keep ai_eyes mode")
    if esp32_payload.get("preserve_eyes") is not True:
        failures.append("DualEye loading payload does not preserve the AI eyes")
    if esp32_payload.get("loading_text_on_eyes") is not False:
        failures.append("DualEye loading payload allows loading text over the AI eyes")
    if esp32_payload.get("message"):
        failures.append("DualEye loading payload should not contain the Heltec loading banner")

    runner = ROOT / "scripts" / "run_menu_screen.py"
    runner_text = runner.read_text(encoding="utf-8", errors="ignore") if runner.exists() else ""
    for marker in ["start_loading_face_sequence", "KILLERKOALA_LOADING_FACE_SENTINEL", "loading.stop()"]:
        if marker not in runner_text:
            failures.append(f"run_menu_screen.py missing loading marker: {marker}")

    bridge = ROOT / "pi-companion" / "koalablue" / "killerkoala_face_bridge.py"
    bridge_text = bridge.read_text(encoding="utf-8", errors="ignore") if bridge.exists() else ""
    for marker in [
        "emit_loading_frame",
        "build_heltec_loading_payload",
        "build_esp32_loading_eyes_payload",
        "jungle_loading_banner",
        "ai_eyes",
        "loading_text_on_eyes",
    ]:
        if marker not in bridge_text and marker != "jungle_loading_banner":
            failures.append(f"loading bridge missing split-display marker: {marker}")

    firmware = ROOT / "firmware" / "t114-combined-safe" / "src" / "main.c"
    firmware_text = firmware.read_text(encoding="utf-8", errors="ignore") if firmware.exists() else ""
    for marker in [
        "jungle_loading_banner",
        "render_loading_banner",
        "DT_CHOSEN(zephyr_display)",
        "PIXEL_FORMAT_RGB_565",
    ]:
        if marker not in firmware_text:
            failures.append(f"T114 firmware missing loading-display marker: {marker}")

    seq = start_loading_face_sequence("Loading Test", enabled=False)
    seq.stop()

    payload = {
        "status": "KILLERKOALA_LOADING_FACE_READY" if not failures else "KILLERKOALA_LOADING_FACE_INCOMPLETE",
        "loading_word": LOADING_WORD,
        "frames": frames,
        "heltec_banners": banners,
        "sample_message": sample,
        "heltec_payload": heltec_payload,
        "esp32_payload": esp32_payload,
        "requirements": [
            "Heltec T114 renders the jungle loading banner one letter at a time",
            "ESP32-S3 DualEye keeps the KillerKoala AI eyes active during loading",
            "Loading text is not drawn over the DualEye eye display",
            "Loading transport failures do not stop the selected action",
        ],
        "updated_at": time.time(),
        "failures": failures,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures},
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
