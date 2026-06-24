#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "logs/koalabyte_external_antenna_status.json": "KOALABYTE_EXTERNAL_ANTENNAS_READY_FOR_HARDWARE_VALIDATION",
    "logs/t114_lora_external_antenna_status.json": "LoRa / SX1262",
    "logs/t114_2g4_antenna_status.json": "connector_physical",
    "logs/esp32s3_dualeye_2g4_antenna_status.json": "ESP32-S3 DualEye",
    "logs/pi_2g4_external_antenna_status.json": "optional_not_required",
}


def main() -> int:
    result = subprocess.run(
        ["bash", "scripts/configure_koalabyte_external_antennas.sh", "--check-only"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return result.returncode

    failures: list[str] = []
    for relative_path, expected_text in EXPECTED.items():
        path = REPO_ROOT / relative_path
        if not path.exists():
            failures.append(f"missing status file: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        if expected_text not in text:
            failures.append(f"{relative_path} missing expected text: {expected_text}")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            failures.append(f"{relative_path} is not valid JSON: {exc}")
            continue
        if relative_path.endswith("pi_2g4_external_antenna_status.json") and payload.get("adapter_required") is not False:
            failures.append("Pi adapter_required must be false")

    if failures:
        print("External antenna readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("External antenna readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
