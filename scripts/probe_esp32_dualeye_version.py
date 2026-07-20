#!/usr/bin/env python3
"""Conservatively identify whether a connected DualEye is current, older, or unknown."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

CURRENT_VERSION = (0, 9, 8)
VERSION_RE = re.compile(r"(?i)(?:firmware|app|dualeye|version)[^\r\n]{0,48}?\bv?(\d+)\.(\d+)\.(\d+)\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=4.0)
    parser.add_argument("--status-path", default="logs/one_shot/esp32_version_probe.json")
    return parser.parse_args()


def write_status(path: str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def classify(transcript: str) -> tuple[str, str, str | None]:
    normalized = transcript.lower().replace(" ", "")
    strict_markers = (
        "wake_session_timeout_ms\":10000" in normalized
        or "wake_session_timeout_ms:10000" in normalized
    ) and (
        "voice_command_ignored_sleeping" in normalized
        or "ten_second_inactivity_timeout" in normalized
        or "wake_session_active" in normalized
    )
    if strict_markers:
        return "current", "strict 10-second wake-session markers detected", "0.9.8+"

    versions = [tuple(map(int, match.groups())) for match in VERSION_RE.finditer(transcript)]
    if versions:
        newest = max(versions)
        rendered = ".".join(map(str, newest))
        if newest < CURRENT_VERSION:
            return "older", f"reported firmware version {rendered} is older than 0.9.8", rendered
        return "current", f"reported firmware version {rendered} is current", rendered
    return "unknown", "no trustworthy DualEye firmware version or strict wake-session marker was found", None


def main() -> int:
    args = parse_args()
    payload: dict[str, Any] = {
        "port": args.port or None,
        "required_version": "0.9.8",
        "classification": "unknown",
        "reason": "probe not run",
        "reported_version": None,
        "updated_at": time.time(),
    }
    if not args.port:
        payload["reason"] = "no serial port supplied"
        write_status(args.status_path, payload)
        print(json.dumps(payload, sort_keys=True))
        return 20

    try:
        import serial  # type: ignore
    except Exception as exc:
        payload["reason"] = f"pyserial unavailable: {exc}"
        write_status(args.status_path, payload)
        print(json.dumps(payload, sort_keys=True))
        return 20

    transcript = bytearray()
    try:
        with serial.Serial(args.port, args.baud, timeout=0.15) as device:
            device.reset_input_buffer()
            device.write(b'{"type":"local_voice_status_request"}\n')
            device.flush()
            deadline = time.monotonic() + max(args.timeout, 0.5)
            while time.monotonic() < deadline:
                chunk = device.read(4096)
                if chunk:
                    transcript.extend(chunk)
    except Exception as exc:
        payload["reason"] = f"serial probe failed: {exc}"
        write_status(args.status_path, payload)
        print(json.dumps(payload, sort_keys=True))
        return 20

    text = transcript.decode("utf-8", errors="replace")
    classification, reason, reported = classify(text)
    payload.update(
        classification=classification,
        reason=reason,
        reported_version=reported,
        transcript_tail=text[-4000:],
        updated_at=time.time(),
    )
    write_status(args.status_path, payload)
    print(json.dumps(payload, sort_keys=True))
    return {"current": 0, "older": 10, "unknown": 20}[classification]


if __name__ == "__main__":
    sys.exit(main())
