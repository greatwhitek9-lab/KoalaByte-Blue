#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    "scripts/deploy_whole_system_firmware.sh": (
        "flash_t114_uf2",
        "flash_esp32_complete_image",
        "sha256sum -c SHA256SUMS.txt",
    ),
    "scripts/flash_esp32_dualeye_current.sh": (
        "0x00cb0000",
        "srmodels.bin",
        "node_status",
    ),
    "scripts/flash_t114_current_uf2.sh": (
        "KOALABYTE.UF2",
        "verify_uf2_vector.py",
        "HT-n5262",
    ),
    "firmware/t114-combined-safe/scripts/patch_uf2_bootloader_entry.py": (
        "GPREGRET = 0x57",
        "koalabyte_bootloader",
        "SYS_REBOOT_COLD",
    ),
}

EXPECTED_ESP32 = {
    "bootloader.bin": "0x00000000",
    "partitions.bin": "0x00008000",
    "boot_app0.bin": "0x0000e000",
    "firmware.bin": "0x00010000",
    "srmodels.bin": "0x00cb0000",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    return failures


def validate_bundle(bundle: Path) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    manifest_path = bundle / "manifest.json"
    if not manifest_path.exists():
        return [f"missing firmware bundle manifest: {manifest_path}"], {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid firmware bundle manifest: {exc}"], {}

    esp32_files = manifest.get("esp32", {}).get("files", [])
    indexed = {str(item.get("path", "")).split("/")[-1]: item for item in esp32_files}
    if manifest.get("esp32", {}).get("included"):
        for name, address in EXPECTED_ESP32.items():
            item = indexed.get(name)
            if not item:
                failures.append(f"ESP32 manifest missing {name}")
                continue
            if str(item.get("flash_address")) != address:
                failures.append(f"ESP32 {name} address is {item.get('flash_address')}, expected {address}")
            path = bundle / str(item.get("path"))
            if not path.exists():
                failures.append(f"ESP32 bundle file missing: {path}")
            elif sha256(path) != item.get("sha256"):
                failures.append(f"ESP32 bundle checksum mismatch: {name}")

    t114 = manifest.get("t114", {})
    if t114.get("included"):
        item = t114.get("file") or {}
        path = bundle / str(item.get("path", ""))
        if not path.exists():
            failures.append(f"T114 UF2 missing: {path}")
        elif sha256(path) != item.get("sha256"):
            failures.append("T114 UF2 checksum mismatch")
        if t114.get("family_id") != "0x239a0071":
            failures.append("T114 UF2 family ID is not 0x239a0071")
        if t114.get("application_offset") != "0x00026000":
            failures.append("T114 application offset is not 0x00026000")
    return failures, manifest


def validate_post_flash(*, skip_esp32: bool, skip_t114: bool) -> list[str]:
    failures: list[str] = []
    status_specs: list[tuple[Path, set[str]]] = []
    if not skip_t114:
        status_specs.append(
            (ROOT / "logs/deployment/t114_flash_status.json", {"flashed"})
        )
    if not skip_esp32:
        status_specs.append(
            (ROOT / "logs/deployment/esp32_flash_status.json", {"flashed"})
        )

    for path, allowed in status_specs:
        if not path.exists():
            failures.append(f"missing post-flash status: {path}")
            continue
        try:
            status = json.loads(path.read_text(encoding="utf-8")).get("status")
        except Exception as exc:
            failures.append(f"unreadable post-flash status {path}: {exc}")
            continue
        if status not in allowed:
            failures.append(f"post-flash status is not verified for {path.name}: {status}")

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

    failures = validate_source()
    manifest: dict[str, Any] = {}
    if args.bundle_only or args.post_flash:
        bundle_failures, manifest = validate_bundle(Path(args.bundle_dir))
        failures.extend(bundle_failures)
    if args.post_flash:
        failures.extend(
            validate_post_flash(
                skip_esp32=args.skip_esp32,
                skip_t114=args.skip_t114,
            )
        )

    payload = {
        "status": "WHOLE_SYSTEM_DEPLOYMENT_READY" if not failures else "WHOLE_SYSTEM_DEPLOYMENT_INCOMPLETE",
        "source_contract": True,
        "bundle_checked": bool(args.bundle_only or args.post_flash),
        "post_flash_checked": bool(args.post_flash),
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
