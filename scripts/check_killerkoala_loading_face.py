#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
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
BOOT_SPLASH_ASSET = ROOT / "firmware" / "t114-combined-safe" / "assets" / "killerkoala-bootsplash-240x135.rgb565be"
BOOT_SPLASH_SHA256 = "7e097b1966de7bc9338a825917be4d71480bae226373eb993cf2ac8e5f0dab26"
BOOT_SPLASH_BYTES = 240 * 135 * 2
MOUTH_ASSET_HASHES = {
    "killerkoala-cyber-mouth-smile-240x135.rgb565be": "4ac8487889927f12245b7aab18bcbae67a136d435bedfbc12d64b6438b325c0b",
    "killerkoala-cyber-mouth-happy-240x135.rgb565be": "16753b3a5ae15a9946c7a519203d181ac4c1d21a121f7de6699497bbc96c4f00",
    "killerkoala-cyber-mouth-bite-240x135.rgb565be": "7473bc86850497c03067fce47f3bd2bdf6166ca0ac1cbc14f19dc579adac93cd",
    "killerkoala-cyber-mouth-snarl-240x135.rgb565be": "265f944b10b4cab58ee0d84b5e67fbec805a2cd7774829641697a3077f058ed0",
    "killerkoala-cyber-mouth-sideways-grin-240x135.rgb565be": "2698c29d589abe9b3582be48f630da71ce0c3051d7656d7f4ba57556fd435e49",
}


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
    if heltec_payload.get("state") != "koalagotchi_action":
        failures.append("Heltec action payload does not enter Koalagotchi state")
    if heltec_payload.get("display_mode") != "koalagotchi_action":
        failures.append("Heltec action payload does not select Koalagotchi animation")
    if heltec_payload.get("frame_index") != 2:
        failures.append("Heltec action payload does not carry the Koalagotchi frame index")
    if heltec_payload.get("message"):
        failures.append("Heltec Koalagotchi payload should not display the action label")
    if len(json.dumps(heltec_payload, separators=(",", ":"))) >= 256:
        failures.append("Heltec loading payload exceeds the T114 USB command-line budget")
    if esp32_payload.get("target_display") != "esp32-s3-dualeye":
        failures.append("DualEye loading payload does not target esp32-s3-dualeye")
    if esp32_payload.get("type") != "menu_sync":
        failures.append("DualEye action payload does not use its existing label renderer")
    if esp32_payload.get("display_mode") != "action_status":
        failures.append("DualEye action payload does not select action-status mode")
    if esp32_payload.get("selected_label") != "Koala Kan Kommander":
        failures.append("DualEye action payload does not display the executing action")
    if esp32_payload.get("animation") != "pulse":
        failures.append("DualEye executing-action label is not animated")
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
        "frame_index",
        "selected_label",
        "action_status",
        "loading_text_on_eyes",
        '"animation": "pulse"',
    ]:
        if marker not in bridge_text:
            failures.append(f"loading bridge missing split-display marker: {marker}")

    firmware = ROOT / "firmware" / "t114-combined-safe" / "src" / "main.c"
    firmware_text = firmware.read_text(encoding="utf-8", errors="ignore") if firmware.exists() else ""
    for marker in ["jungle_loading_banner", "render_loading_banner", "loading_display_init"]:
        if marker not in firmware_text:
            failures.append(f"T114 firmware missing loading-state marker: {marker}")

    renderer = ROOT / "firmware" / "t114-combined-safe" / "src" / "loading_display.c"
    renderer_text = renderer.read_text(encoding="utf-8", errors="ignore") if renderer.exists() else ""
    for marker in [
        "DT_CHOSEN(zephyr_display)",
        "PIXEL_FORMAT_RGB_565",
        "draw_jungle_frame",
        "draw_centered_banner",
        "killerkoala_boot_splash_rgb565_be",
        "render_killerkoala_boot_splash",
        "draw_koalagotchi_action_frame",
        "render_koalagotchi_action",
        "render_killerkoala_mouth",
        "blend_rgb565_be",
        "render_menu_status",
    ]:
        if marker not in renderer_text:
            failures.append(f"T114 display renderer missing marker: {marker}")

    if not BOOT_SPLASH_ASSET.exists():
        failures.append(f"T114 boot splash asset missing: {BOOT_SPLASH_ASSET.relative_to(ROOT)}")
    else:
        boot_splash = BOOT_SPLASH_ASSET.read_bytes()
        if len(boot_splash) != BOOT_SPLASH_BYTES:
            failures.append(f"T114 boot splash must be {BOOT_SPLASH_BYTES} bytes, got {len(boot_splash)}")
        boot_splash_sha256 = hashlib.sha256(boot_splash).hexdigest()
        if boot_splash_sha256 != BOOT_SPLASH_SHA256:
            failures.append(f"T114 boot splash SHA-256 mismatch: {boot_splash_sha256}")

    for filename, expected_hash in MOUTH_ASSET_HASHES.items():
        prefix = BOOT_SPLASH_ASSET.parent / f"{filename}.b64"
        parts = [Path(f"{prefix}.part0"), Path(f"{prefix}.part1")]
        missing = [part for part in parts if not part.exists()]
        if missing:
            failures.extend(f"T114 cyber-mouth asset part missing: {part.relative_to(ROOT)}" for part in missing)
            continue
        encoded = "".join("".join(part.read_text(encoding="ascii").split()) for part in parts)
        try:
            payload_bytes = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            failures.append(f"T114 cyber-mouth base64 is invalid for {filename}: {exc}")
            continue
        if len(payload_bytes) != BOOT_SPLASH_BYTES:
            failures.append(f"T114 cyber-mouth asset {filename} must be {BOOT_SPLASH_BYTES} bytes, got {len(payload_bytes)}")
        digest = hashlib.sha256(payload_bytes).hexdigest()
        if digest != expected_hash:
            failures.append(f"T114 cyber-mouth SHA-256 mismatch for {filename}: {digest}")

    power_init = ROOT / "firmware" / "t114-combined-safe" / "src" / "display_power_init.c"
    power_text = power_init.read_text(encoding="utf-8", errors="ignore") if power_init.exists() else ""
    for marker in ["SYS_INIT", "POST_KERNEL", "vext_control", "tft_enable", "tft_backlight"]:
        if marker not in power_text:
            failures.append(f"T114 early display power initializer missing marker: {marker}")

    cmake = ROOT / "firmware" / "t114-combined-safe" / "CMakeLists.txt"
    cmake_text = cmake.read_text(encoding="utf-8", errors="ignore") if cmake.exists() else ""
    for marker in ["src/display_power_init.c", "src/loading_display.c"]:
        if marker not in cmake_text:
            failures.append(f"T114 build does not include loading display source: {marker}")

    esp32_firmware = ROOT / "firmware" / "esp32-dualeye" / "src" / "main.cpp"
    esp32_text = esp32_firmware.read_text(encoding="utf-8", errors="ignore") if esp32_firmware.exists() else ""
    for marker in ["handleKillerKoalaFace", "setKoalagotchiEyeStyle", "killerkoala_eye_ack"]:
        if marker not in esp32_text:
            failures.append(f"DualEye firmware missing active-eye marker: {marker}")

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
            "Heltec T114 boots through the supplied artwork and plays Koalagotchi during actions",
            "T114 smile, bite, snarl, and sideways-grin frames follow Koalagotchi contentment and mood",
            "T114 mouth poses use eased RGB565 interpolation and cycle naturally while idle",
            "T114 speaking mouth follows explicit Pi/local-AI speech start and stop events",
            "T114 display power is asserted before the ST7789 display driver initializes",
            "ESP32-S3 DualEye displays the name of every executing menu action",
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
