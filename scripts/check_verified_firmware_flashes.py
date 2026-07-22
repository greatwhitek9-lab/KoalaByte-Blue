#!/usr/bin/env python3
"""Verify that both boards reported the exact runtime identities in the bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "releases/koalabyte-blue-current"
DEFAULT_ESP32_STATUS = ROOT / "logs/deployment/esp32_flash_status.json"
DEFAULT_T114_STATUS = ROOT / "logs/deployment/t114_flash_status.json"
IDENTITY_KEYS = ("device", "fw", "protocol", "repo_protocol_version")


def load(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"required deployment record is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def normalized(identity: object, label: str) -> dict[str, str]:
    if not isinstance(identity, dict):
        raise RuntimeError(f"{label} identity is missing")
    output: dict[str, str] = {}
    for key in IDENTITY_KEYS:
        value = str(identity.get(key) or "").strip()
        if not value:
            raise RuntimeError(f"{label} identity is missing {key}")
        output[key] = value
    return output


def verify_board(
    board: str,
    bundle_identity: object,
    status: dict[str, object],
) -> dict[str, str]:
    if status.get("status") != "flashed":
        raise RuntimeError(
            f"{board} flash receipt is not successful: {status.get('status')!r}"
        )
    expected = normalized(bundle_identity, f"{board} bundle")
    recorded_expected = normalized(
        status.get("expected_runtime_identity"), f"{board} recorded expected"
    )
    observed = normalized(
        status.get("observed_runtime_identity"), f"{board} observed"
    )
    if recorded_expected != expected:
        raise RuntimeError(
            f"{board} flash receipt expected identity does not match bundle: "
            f"bundle={expected} receipt={recorded_expected}"
        )
    if observed != expected:
        raise RuntimeError(
            f"{board} observed identity does not match bundle: "
            f"bundle={expected} observed={observed}"
        )
    return observed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--esp32-status", type=Path, default=DEFAULT_ESP32_STATUS)
    parser.add_argument("--t114-status", type=Path, default=DEFAULT_T114_STATUS)
    args = parser.parse_args()

    manifest = load(args.bundle / "manifest.json")
    esp32_section = manifest.get("esp32")
    t114_section = manifest.get("t114")
    if not isinstance(esp32_section, dict) or not isinstance(t114_section, dict):
        raise RuntimeError("firmware bundle manifest is missing board sections")
    if not esp32_section.get("included") or not t114_section.get("included"):
        raise RuntimeError("full flash verification requires both boards in the bundle")

    esp32 = verify_board(
        "esp32",
        esp32_section.get("runtime_identity"),
        load(args.esp32_status),
    )
    t114 = verify_board(
        "t114",
        t114_section.get("runtime_identity"),
        load(args.t114_status),
    )
    print(
        json.dumps(
            {
                "status": "BOTH_FIRMWARE_FLASHES_VERIFIED",
                "bundle": str(args.bundle.resolve()),
                "source_commit": manifest.get("source_commit"),
                "esp32": esp32,
                "t114": t114,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
