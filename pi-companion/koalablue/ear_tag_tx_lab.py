from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List


@dataclass
class EarTagTxLabPlan:
    action: str
    mode: str
    created_at: float
    device_name: str
    firmware_path: str
    board: str
    build_command: str
    package_command: str
    flash_command: str
    safe_scope: str
    synthetic_payload: str
    observation_steps: List[str]


def write_ear_tag_tx_lab_plan(output_dir: str | Path = "logs/ear_tag_tx_lab") -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    now = time.time()
    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(now))
    plan = EarTagTxLabPlan(
        action="Ear Tag TX Lab",
        mode="synthetic_owned_lab_ble_advertisement",
        created_at=now,
        device_name="EarTag-TX-Lab",
        firmware_path="firmware/nrf52840-dongle-ear-tag-tx-lab",
        board="nrf52840dongle_nrf52840",
        build_command="west build -b nrf52840dongle_nrf52840 firmware/nrf52840-dongle-ear-tag-tx-lab -d build/nrf52840-dongle-lab",
        package_command="bash scripts/flash_nrf52840_dongle_lab_dfu.sh",
        flash_command="NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh",
        safe_scope="Synthetic owned-device BLE advertisement for signal-integrity observation. No captured packet replay.",
        synthetic_payload="128-bit service-data block with KBTX magic, static pattern bytes, sequence counter, and XOR check byte.",
        observation_steps=[
            "Build the nRF52840 Dongle Ear Tag TX Lab firmware.",
            "Put the nRF52840 Dongle into bootloader mode.",
            "Create the DFU package and flash through the detected DFU serial port.",
            "Scan passively and confirm the device name EarTag-TX-Lab.",
            "Observe the KBTX service-data sequence counter changing every refresh interval.",
            "Use RSSI, missing sequence numbers, and scan logs for signal-integrity notes.",
            "Keep the Dongle physically labeled as KoalaByte Blue lab hardware inside the authorized test area.",
        ],
    )
    out = root / f"ear_tag_tx_lab_plan_{stamp}.json"
    out.write_text(json.dumps(asdict(plan), indent=2, sort_keys=True), encoding="utf-8")
    return out


def run_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Write an Ear Tag TX Lab setup plan")
    parser.add_argument("--output-dir", default="logs/ear_tag_tx_lab")
    args = parser.parse_args()
    path = write_ear_tag_tx_lab_plan(args.output_dir)
    print(json.dumps({"action": "Ear Tag TX Lab", "plan_path": str(path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
