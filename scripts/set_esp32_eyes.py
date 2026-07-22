#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.serial_command_bus import submit_command  # noqa: E402
from koalablue.serial_maintenance import (  # noqa: E402
    require_direct_serial_maintenance,
)

LOOKS = ["round", "cyber", "slit", "sleepy", "angry", "star", "heart", "x"]
ANIMATIONS = ["static", "idle", "pulse", "blink", "scan", "glitch", "sleepy"]

PRESETS = {
    "killerkoala": {
        "look": "cyber",
        "left_color": "#A54BFF",
        "right_color": "#32FF71",
        "animation": "pulse",
        "brightness": 100,
    },
    "eucalyptus": {
        "look": "round",
        "left_color": "#7B2CFF",
        "right_color": "#32FF71",
        "animation": "pulse",
        "brightness": 100,
    },
    "boomerang": {
        "look": "angry",
        "left_color": "#FF9A26",
        "right_color": "#FFE24E",
        "animation": "scan",
        "brightness": 100,
    },
    "greatwhite": {
        "look": "slit",
        "left_color": "#67C7FF",
        "right_color": "#E8FFE8",
        "animation": "scan",
        "brightness": 95,
    },
    "sleepy": {
        "look": "sleepy",
        "left_color": "#6EA8FF",
        "right_color": "#6EA8FF",
        "animation": "sleepy",
        "brightness": 70,
    },
    "love": {
        "look": "heart",
        "left_color": "#FF4FA3",
        "right_color": "#FF4FA3",
        "animation": "pulse",
        "brightness": 100,
    },
    "legend": {
        "look": "star",
        "left_color": "#FFE24E",
        "right_color": "#32FF71",
        "animation": "glitch",
        "brightness": 100,
    },
}


def build_payload(args: argparse.Namespace) -> dict[str, object]:
    if args.reset:
        return {"type": "eye_style", "reset": True}
    payload = dict(PRESETS.get(args.preset, PRESETS["killerkoala"]))
    if args.look:
        payload["look"] = args.look
    if args.left:
        payload["left_color"] = args.left
    if args.right:
        payload["right_color"] = args.right
    if args.animation:
        payload["animation"] = args.animation
    if args.brightness is not None:
        payload["brightness"] = max(1, min(100, args.brightness))
    payload["type"] = "eye_style"
    payload["mode"] = args.mode
    payload["mood"] = args.mood
    payload["contentment"] = args.contentment
    payload["xp_percent"] = args.xp_percent
    payload["source"] = "set-esp32-eyes"
    return payload


def send_direct(port: str, baud: int, payload: dict[str, object], wait: float) -> None:
    require_direct_serial_maintenance(
        "esp32",
        env_var="KOALABYTE_ALLOW_DIRECT_ESP32_SERIAL",
        service_name="koalabyte-dualeye-voice-bridge.service",
    )
    try:
        import serial  # type: ignore
    except Exception as exc:
        raise SystemExit(
            "pyserial is required. Install the Pi companion requirements first."
        ) from exc
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    with serial.Serial(port, baudrate=baud, timeout=wait) as ser:  # type: ignore[attr-defined]
        ser.write(line.encode("utf-8"))
        ser.flush()
        time.sleep(wait)
        while ser.in_waiting:
            sys.stdout.write(ser.readline().decode("utf-8", errors="replace"))


def submit_to_owner(payload: dict[str, object]) -> str:
    result = submit_command(
        "esp32",
        payload,
        queue_if_unavailable=False,
    )
    if not result.accepted or not result.delivered:
        raise RuntimeError(
            f"ESP32 owner did not accept the eye-style command: {result.status}"
        )
    return result.status


def write_profile(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set KoalaByte Blue ESP32-S3 DualEye custom animated eyes"
    )
    parser.add_argument(
        "--port",
        default=os.getenv("KOALABYTE_ESP32_FACE_PORT", "/dev/koalabyte-esp32-dualeye"),
        help="Used only with --direct-serial",
    )
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--preset", choices=sorted(PRESETS), default="killerkoala")
    parser.add_argument("--look", choices=LOOKS)
    parser.add_argument("--left", help="Left eye color, #RRGGBB")
    parser.add_argument("--right", help="Right eye color, #RRGGBB")
    parser.add_argument("--animation", choices=ANIMATIONS)
    parser.add_argument("--brightness", type=int)
    parser.add_argument("--mode", default="eucalyptus")
    parser.add_argument("--mood", default="custom")
    parser.add_argument("--contentment", type=int, default=75)
    parser.add_argument("--xp-percent", type=int, default=88)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--save-profile", type=Path, help="Write the JSON profile")
    parser.add_argument(
        "--preview-only", action="store_true", help="Only print the JSON payload"
    )
    parser.add_argument(
        "--direct-serial",
        action="store_true",
        help=(
            "Manual maintenance only; requires KOALABYTE_ALLOW_DIRECT_ESP32_SERIAL=1 "
            "and a stopped voice-bridge owner service"
        ),
    )
    args = parser.parse_args()

    payload = build_payload(args)
    if args.save_profile:
        write_profile(args.save_profile, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.preview_only:
        return 0
    if args.direct_serial:
        send_direct(args.port, args.baud, payload, 0.4)
        mode = "direct_manual_owner_stopped"
    else:
        mode = submit_to_owner(payload)
    print(json.dumps({"status": "ESP32_EYE_STYLE_SUBMITTED", "mode": mode}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
