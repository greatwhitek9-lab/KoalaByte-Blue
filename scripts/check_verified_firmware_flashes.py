#!/usr/bin/env python3
"""Verify that selected boards reported the exact identities in the bundle."""

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
    bundle_section: object,
    status: dict[str, object],
) -> dict[str, str]:
    if not isinstance(bundle_section, dict):
        raise RuntimeError(f"firmware bundle is missing {board} section")
    if not bundle_section.get("included"):
        raise RuntimeError(f"firmware bundle does not include required board: {board}")
    if status.get("status") != "flashed":
        raise RuntimeError(
            f"{board} flash receipt is not successful: {status.get('status')!r}"
        )
    expected = normalized(bundle_section.get("runtime_identity"), f"{board} bundle")
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
    parser.add_argument("--require", choices=("all", "esp32", "t114"), default="all")
    args = parser.parse_args()

    manifest = load(args.bundle / "manifest.json")
    result: dict[str, object] = {
        "status": "FIRMWARE_FLASH_RECEIPTS_VERIFIED",
        "bundle": str(args.bundle.resolve()),
        "source_commit": manifest.get("source_commit"),
        "required": args.require,
    }
    if args.require in {"all", "esp32"}:
        result["esp32"] = verify_board(
            "esp32", manifest.get("esp32"), load(args.esp32_status)
        )
    if args.require in {"all", "t114"}:
        result["t114"] = verify_board(
            "t114", manifest.get("t114"), load(args.t114_status)
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
