#!/usr/bin/env python3
"""Regression guard for recovery-capable firmware device preflight.

The outer deploy wrapper must not reject a board merely because it is already in
its bootloader/download state. T114 recovery is accepted by UF2 volume identity;
ESP32 identity is owned by the flasher's non-destructive esptool chip_id probe.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts/deploy_whole_system_firmware.sh"
ESP32_FLASH = ROOT / "scripts/flash_esp32_dualeye_current.sh"
T114_BOOT = ROOT / "scripts/enter_t114_uf2_bootloader.sh"


def require(text: str, markers: tuple[str, ...], label: str) -> list[str]:
    return [f"{label} missing recovery preflight marker: {marker}" for marker in markers if marker not in text]


def main() -> int:
    failures: list[str] = []
    deploy = DEPLOY.read_text(encoding="utf-8")
    esp32 = ESP32_FLASH.read_text(encoding="utf-8")
    t114_boot = T114_BOOT.read_text(encoding="utf-8")

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
                "ESP32-S3 presence will be validated by the non-destructive chip_id probe",
            ),
            "deploy wrapper",
        )
    )
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

    obsolete = "ESP32-S3 DualEye was not detected immediately before flashing."
    if obsolete in deploy:
        failures.append("deploy wrapper still rejects ESP32 by runtime filename before chip_id probing")

    chip_probe = deploy.find("discover_required_devices")
    t114_flash = deploy.find('CURRENT_STEP="flash_t114_uf2"')
    esp32_flash = deploy.find('CURRENT_STEP="flash_esp32_complete_image"')
    if chip_probe < 0 or t114_flash < 0 or esp32_flash < 0:
        failures.append("deployment stage ordering markers are incomplete")
    elif not (chip_probe < t114_flash < esp32_flash):
        failures.append("device preflight must run before both board flash stages")

    payload = {
        "status": "FLASH_RECOVERY_PREFLIGHT_READY" if not failures else "FLASH_RECOVERY_PREFLIGHT_INCOMPLETE",
        "t114_runtime_or_uf2_accepted": not failures,
        "esp32_chip_id_is_authoritative": not failures,
        "esp32_filename_only_rejection_removed": obsolete not in deploy,
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
