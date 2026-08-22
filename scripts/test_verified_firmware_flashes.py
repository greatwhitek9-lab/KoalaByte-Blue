#!/usr/bin/env python3
"""Regression tests for exact firmware flash receipt verification."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_verified_firmware_flashes.py"

ESP32_ID = {
    "device": "esp32-s3-dualeye",
    "fw": "0.9.8-dualeye-static-grammar-40-response-bank",
    "protocol": "menu_sync_v1",
    "repo_protocol_version": "2026.06-menu-sync-v1",
}
T114_ID = {
    "device": "heltec-t114",
    "fw": "0.10.0-t114-smooth-idle-and-speech-mouth",
    "protocol": "killerkoala_face_v1",
    "repo_protocol_version": "2026.06-menu-sync-v1",
}


def write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def receipt(identity: dict[str, str], *, updated_at: float, status: str = "flashed") -> dict[str, object]:
    return {
        "status": status,
        "expected_runtime_identity": dict(identity),
        "observed_runtime_identity": dict(identity),
        "updated_at": updated_at,
    }


def run(bundle: Path, esp32: Path, t114: Path, requirement: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--bundle",
            str(bundle),
            "--esp32-status",
            str(esp32),
            "--t114-status",
            str(t114),
            "--require",
            requirement,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def expect_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise AssertionError(f"{label} unexpectedly failed:\n{result.stdout}")


def expect_failure(result: subprocess.CompletedProcess[str], needle: str, label: str) -> None:
    if result.returncode == 0:
        raise AssertionError(f"{label} unexpectedly passed:\n{result.stdout}")
    if needle not in result.stdout:
        raise AssertionError(
            f"{label} failed for the wrong reason; expected {needle!r}:\n{result.stdout}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="koalabyte-flash-receipts-") as temp_dir:
        temp = Path(temp_dir)
        bundle = temp / "bundle"
        esp32_status = temp / "esp32.json"
        t114_status = temp / "t114.json"
        built_at = 1_800_000_000.0
        manifest = {
            "schema": 2,
            "bundle": "koalabyte-blue-current",
            "source_commit": "deadbeef",
            "built_at": built_at,
            "esp32": {"included": True, "runtime_identity": dict(ESP32_ID)},
            "t114": {"included": True, "runtime_identity": dict(T114_ID)},
        }
        write(bundle / "manifest.json", manifest)
        write(esp32_status, receipt(ESP32_ID, updated_at=built_at + 10))
        write(t114_status, receipt(T114_ID, updated_at=built_at + 11))

        expect_success(run(bundle, esp32_status, t114_status, "all"), "matching receipts")

        write(esp32_status, receipt(ESP32_ID, updated_at=built_at - 1))
        expect_failure(
            run(bundle, esp32_status, t114_status, "all"),
            "predates the current firmware bundle",
            "stale ESP32 receipt",
        )
        write(esp32_status, receipt(ESP32_ID, updated_at=built_at + 10))

        wrong_fw = receipt(ESP32_ID, updated_at=built_at + 10)
        observed = dict(ESP32_ID)
        observed["fw"] = "old-firmware"
        wrong_fw["observed_runtime_identity"] = observed
        write(esp32_status, wrong_fw)
        expect_failure(
            run(bundle, esp32_status, t114_status, "esp32"),
            "observed identity does not match bundle",
            "wrong ESP32 firmware",
        )
        write(esp32_status, receipt(ESP32_ID, updated_at=built_at + 10))

        wrong_protocol = receipt(T114_ID, updated_at=built_at + 11)
        observed_t114 = dict(T114_ID)
        observed_t114["protocol"] = "wrong_protocol"
        wrong_protocol["observed_runtime_identity"] = observed_t114
        write(t114_status, wrong_protocol)
        expect_failure(
            run(bundle, esp32_status, t114_status, "t114"),
            "observed identity does not match bundle",
            "wrong T114 protocol",
        )
        write(t114_status, receipt(T114_ID, updated_at=built_at + 11))

        partial_manifest = dict(manifest)
        partial_manifest["esp32"] = {"included": False, "runtime_identity": dict(ESP32_ID)}
        write(bundle / "manifest.json", partial_manifest)
        expect_success(run(bundle, esp32_status, t114_status, "t114"), "T114-only receipt")
        expect_failure(
            run(bundle, esp32_status, t114_status, "esp32"),
            "does not include required board",
            "excluded ESP32 requirement",
        )

    print(
        json.dumps(
            {
                "status": "FIRMWARE_FLASH_RECEIPT_TESTS_READY",
                "matching_receipts": True,
                "stale_receipts_rejected": True,
                "wrong_firmware_rejected": True,
                "wrong_protocol_rejected": True,
                "partial_requirements_supported": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
