#!/usr/bin/env python3
"""Regression guard for recovery-capable, transactional firmware preflight.

All selected targets must be proven before the first firmware write. T114 may be
present as runtime USB or its UF2 recovery volume. ESP32-S3 must answer a
non-writing esptool chip_id probe before T114 flashing starts, and its flasher
must still repeat the identity probe immediately before write_flash. On actual
Raspberry Pi hardware, strict power mode must fail closed when vcgencmd power
state is unavailable or unparseable, and the one-shot package stage must install
the Raspberry Pi utility package that supplies that probe path.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts/deploy_whole_system_firmware.sh"
ESP32_PROBE = ROOT / "scripts/probe_esp32_s3.sh"
ESP32_FLASH = ROOT / "scripts/flash_esp32_dualeye_current.sh"
T114_BOOT = ROOT / "scripts/enter_t114_uf2_bootloader.sh"
HOST_PREFLIGHT = ROOT / "scripts/preflight_firmware_host.sh"
SYSTEM_PACKAGES = ROOT / "scripts/setup_system_packages.sh"


def require(text: str, markers: tuple[str, ...], label: str) -> list[str]:
    return [
        f"{label} missing recovery/transactional preflight marker: {marker}"
        for marker in markers
        if marker not in text
    ]


def main() -> int:
    failures: list[str] = []
    deploy = DEPLOY.read_text(encoding="utf-8")
    esp32_probe = ESP32_PROBE.read_text(encoding="utf-8")
    esp32 = ESP32_FLASH.read_text(encoding="utf-8")
    t114_boot = T114_BOOT.read_text(encoding="utf-8")
    host = HOST_PREFLIGHT.read_text(encoding="utf-8")
    packages = SYSTEM_PACKAGES.read_text(encoding="utf-8")

    failures.extend(
        require(
            deploy,
            (
                'T114_UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"',
                "t114_uf2_present()",
                "lsblk -pnro LABEL,FSTYPE",
                '($2 == "vfat" || $2 == "fat")',
                "Heltec T114 recovery UF2 volume detected",
                "runtime USB or ${T114_UF2_VOLUME_NAME} UF2 recovery volume",
                "bash scripts/probe_esp32_s3.sh",
                "source logs/preflight/esp32_chip_probe.env",
                "export ESP32_PORT KOALABYTE_ESP32_FACE_PORT",
                "every selected target must be proven before the first write",
                '"transactional_target_preflight": True',
            ),
            "deploy wrapper",
        )
    )
    failures.extend(
        require(
            esp32_probe,
            (
                "probe_esp32s3()",
                "--chip esp32s3",
                "--after no_reset chip_id",
                '"non_writing": True',
                "ESP32-S3 preflight verified:",
                "esp32_chip_probe.env",
            ),
            "ESP32 preflight probe",
        )
    )
    if "write_flash" in esp32_probe:
        failures.append("ESP32 global preflight helper must never contain write_flash")

    failures.extend(
        require(
            esp32,
            (
                "probe_esp32s3()",
                "--chip esp32s3",
                "--after no_reset chip_id",
                "write_flash -z",
                "No serial candidate answered an ESP32-S3 chip_id probe.",
            ),
            "ESP32 flasher",
        )
    )
    failures.extend(
        require(
            t114_boot,
            (
                'UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"',
                "UF2_ALREADY_PRESENT",
                "existing=\"$(find_uf2_device || true)\"",
            ),
            "T114 bootloader helper",
        )
    )
    failures.extend(
        require(
            host,
            (
                '[[ "${model}" == *"Raspberry Pi"* ]] && is_raspberry_pi=1',
                "vcgencmd is unavailable on Raspberry Pi hardware",
                "strict power preflight requires a valid vcgencmd get_throttled result",
                '"strict_power_unknown_is_failure": True',
            ),
            "firmware host preflight",
        )
    )
    failures.extend(
        require(
            packages,
            (
                "util-linux raspi-utils libusb-1.0-0",
                "aplay vcgencmd",
                "requires Raspberry Pi power-state tooling for strict preflight",
            ),
            "system package setup",
        )
    )

    obsolete = "ESP32-S3 DualEye was not detected immediately before flashing."
    if obsolete in deploy:
        failures.append(
            "deploy wrapper still rejects ESP32 by runtime filename before chip_id probing"
        )

    device_preflight_call = deploy.find("discover_required_devices\n")
    t114_flash = deploy.find('CURRENT_STEP="flash_t114_uf2"')
    esp32_flash = deploy.find('CURRENT_STEP="flash_esp32_complete_image"')
    if device_preflight_call < 0 or t114_flash < 0 or esp32_flash < 0:
        failures.append("deployment stage ordering markers are incomplete")
    elif not (device_preflight_call < t114_flash < esp32_flash):
        failures.append("transactional device preflight must run before both board flash stages")

    function_start = deploy.find("discover_required_devices()")
    function_end = deploy.find('CURRENT_STEP="source_contract"')
    if function_start < 0 or function_end <= function_start:
        failures.append("could not isolate discover_required_devices for ordering check")
    else:
        preflight_body = deploy[function_start:function_end]
        probe_position = preflight_body.find("bash scripts/probe_esp32_s3.sh")
        if probe_position < 0:
            failures.append("ESP32 chip_id probe is absent from global device preflight")

    payload = {
        "status": (
            "FLASH_TRANSACTIONAL_PREFLIGHT_READY"
            if not failures
            else "FLASH_TRANSACTIONAL_PREFLIGHT_INCOMPLETE"
        ),
        "t114_runtime_or_uf2_accepted": not failures,
        "esp32_global_chip_id_required": not failures,
        "esp32_chip_id_repeated_before_write": not failures,
        "no_selected_target_written_before_global_probe": not failures,
        "strict_pi_power_unknown_rejected": not failures,
        "pi_power_tooling_installed": not failures,
        "esp32_filename_only_rejection_removed": obsolete not in deploy,
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
