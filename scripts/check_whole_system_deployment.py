#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "releases" / "koalabyte-blue-current"
STATUS_PATH = ROOT / "logs" / "deployment" / "whole_system_readiness.json"

REQUIRED_SOURCE_FILES = (
    "one-shot-install.sh",
    "scripts/build_whole_system_firmware.sh",
    "scripts/deploy_whole_system_firmware.sh",
    "scripts/flash_esp32_dualeye_current.sh",
    "scripts/flash_t114_current_uf2.sh",
    "scripts/enter_t114_uf2_bootloader.sh",
    "scripts/build_t114_combined_safe.sh",
    "scripts/setup_esp32_tools.sh",
    "scripts/setup_nrf_connect_sdk_toolchain.sh",
    "scripts/inspect_uf2.py",
    "scripts/patch_uf2_family.py",
    "scripts/verify_uf2_vector.py",
    "scripts/check_firmware_hardware_contract.py",
    "scripts/check_firmware_protocol_contract.py",
    "scripts/check_esp32_compiled_patch_chain.py",
    "scripts/write_firmware_bundle_manifest.py",
    "scripts/check_firmware_bundle.py",
    "scripts/check_verified_firmware_flashes.py",
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/esp32-dualeye/partitions.csv",
    "firmware/t114-combined-safe/CMakeLists.txt",
    "firmware/t114-combined-safe/prj.conf",
    "firmware/t114-combined-safe/scripts/patch_uf2_bootloader_entry.py",
)

SOURCE_MARKERS = {
    "one-shot-install.sh": (
        "scripts/deploy_whole_system_firmware.sh",
        "firmware_flashing",
    ),
    "scripts/build_whole_system_firmware.sh": (
        "check_firmware_hardware_contract.py",
        "check_firmware_protocol_contract.py",
        "write_firmware_bundle_manifest.py",
        "check_firmware_bundle.py",
    ),
    "scripts/deploy_whole_system_firmware.sh": (
        "flash_t114_uf2",
        "flash_esp32_complete_image",
        "check_firmware_bundle.py",
    ),
    "scripts/flash_esp32_dualeye_current.sh": (
        "0x00cb0000",
        "srmodels.bin",
        "expected_repo_protocol",
        "check_firmware_bundle.py",
    ),
    "scripts/flash_t114_current_uf2.sh": (
        "KOALABYTE.UF2",
        "verify_uf2_vector.py",
        "expected_repo_protocol",
        "check_firmware_bundle.py",
    ),
    "firmware/t114-combined-safe/scripts/patch_uf2_bootloader_entry.py": (
        "GPREGRET = 0x57",
        "koalabyte_bootloader",
        "SYS_REBOOT_COLD",
    ),
}


def validate_source() -> list[str]:
    failures: list[str] = []
    for relative in REQUIRED_SOURCE_FILES:
        if not (ROOT / relative).exists():
            failures.append(f"missing deployment source file: {relative}")
    for relative, markers in SOURCE_MARKERS.items():
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            if marker not in text:
                failures.append(f"{relative} missing deployment marker: {marker}")
    partitions = ROOT / "firmware/esp32-dualeye/partitions.csv"
    if partitions.exists() and "0xCB0000" not in partitions.read_text(encoding="utf-8"):
        failures.append("ESP32 speech-model partition is not fixed at 0xCB0000")
    prj = ROOT / "firmware/t114-combined-safe/prj.conf"
    if prj.exists():
        text = prj.read_text(encoding="utf-8")
        if "CONFIG_BUILD_OUTPUT_UF2=y" not in text:
            failures.append("T114 build does not produce UF2")
        if "CONFIG_REBOOT=y" not in text:
            failures.append("T114 firmware cannot software-reboot into UF2")
    for checker in (
        "scripts/check_firmware_hardware_contract.py",
        "scripts/check_firmware_protocol_contract.py",
        "scripts/check_esp32_compiled_patch_chain.py",
    ):
        path = ROOT / checker
        if not path.exists():
            continue
        result = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode:
            failures.append(f"source checker failed: {checker}: {result.stdout.strip()}")
    return failures


def load_manifest(bundle: Path) -> tuple[dict[str, Any], list[str]]:
    path = bundle / "manifest.json"
    if not path.is_file():
        return {}, [f"missing firmware bundle manifest: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, [f"invalid firmware bundle manifest: {exc}"]
    if not isinstance(value, dict):
        return {}, ["firmware bundle manifest is not an object"]
    return value, []


def selected_requirement(manifest: dict[str, Any]) -> str:
    esp32 = bool((manifest.get("esp32") or {}).get("included"))
    t114 = bool((manifest.get("t114") or {}).get("included"))
    if esp32 and t114:
        return "all"
    if esp32:
        return "esp32"
    if t114:
        return "t114"
    raise RuntimeError("firmware bundle includes neither board")


def run_validator(arguments: list[str], label: str) -> list[str]:
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode:
        return [f"{label} failed: {result.stdout.strip()}"]
    return []


def validate_bundle(bundle: Path) -> tuple[list[str], dict[str, Any]]:
    manifest, failures = load_manifest(bundle)
    if failures:
        return failures, manifest
    try:
        requirement = selected_requirement(manifest)
    except Exception as exc:
        return [str(exc)], manifest
    failures.extend(
        run_validator(
            [
                str(ROOT / "scripts/check_firmware_bundle.py"),
                "--bundle",
                str(bundle),
                "--require",
                requirement,
            ],
            "schema-2 firmware bundle validation",
        )
    )
    return failures, manifest


def validate_post_flash(
    bundle: Path, *, skip_esp32: bool, skip_t114: bool
) -> list[str]:
    if skip_esp32 and skip_t114:
        return ["post-flash validation cannot skip both boards"]
    requirement = "all"
    if skip_esp32:
        requirement = "t114"
    elif skip_t114:
        requirement = "esp32"
    failures = run_validator(
        [
            str(ROOT / "scripts/check_verified_firmware_flashes.py"),
            "--bundle",
            str(bundle),
            "--require",
            requirement,
        ],
        "exact firmware flash receipt validation",
    )
    if os.name == "posix" and Path("/dev").exists():
        if not skip_esp32 and not Path("/dev/koalabyte-esp32-dualeye").exists():
            failures.append("ESP32 stable runtime alias missing after flash")
        if not skip_t114 and not (
            Path("/dev/koalabyte-heltec").exists()
            or Path("/dev/koalabyte-heltec-t114").exists()
        ):
            failures.append("T114 stable runtime alias missing after flash")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate whole-system firmware build and deployment")
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--bundle-only", action="store_true")
    parser.add_argument("--post-flash", action="store_true")
    parser.add_argument("--skip-esp32", action="store_true")
    parser.add_argument("--skip-t114", action="store_true")
    parser.add_argument("--bundle-dir", default=str(DEFAULT_BUNDLE))
    args = parser.parse_args()

    bundle = Path(args.bundle_dir)
    failures = validate_source()
    manifest: dict[str, Any] = {}
    if args.bundle_only or args.post_flash:
        bundle_failures, manifest = validate_bundle(bundle)
        failures.extend(bundle_failures)
    if args.post_flash:
        failures.extend(
            validate_post_flash(
                bundle,
                skip_esp32=args.skip_esp32,
                skip_t114=args.skip_t114,
            )
        )

    payload = {
        "status": "WHOLE_SYSTEM_DEPLOYMENT_READY" if not failures else "WHOLE_SYSTEM_DEPLOYMENT_INCOMPLETE",
        "source_contract": True,
        "bundle_checked": bool(args.bundle_only or args.post_flash),
        "post_flash_checked": bool(args.post_flash),
        "exact_flash_identity_checked": bool(args.post_flash),
        "esp32_skipped": args.skip_esp32,
        "t114_skipped": args.skip_t114,
        "bundle_source_commit": manifest.get("source_commit") if manifest else None,
        "installer": "one-shot-install.sh",
        "firmware_targets": ["heltec-t114-uf2", "waveshare-esp32-s3-dualeye"],
        "can_transmit": False,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
