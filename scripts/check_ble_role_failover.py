#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.ble_role_coordinator import (  # noqa: E402
    elect_ble_roles,
    esp32_role_command,
)

STATUS_PATH = ROOT / "logs" / "ble_nodes" / "ble_failover_readiness.json"


def require_marker(path: Path, marker: str, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"missing BLE failover file: {path.relative_to(ROOT)}")
        return
    if marker not in path.read_text(encoding="utf-8", errors="ignore"):
        failures.append(f"{path.relative_to(ROOT)} missing marker: {marker}")


def main() -> int:
    failures: list[str] = []
    previous = os.environ.get("KOALABYTE_PI_BLUEZ_NODE")
    os.environ["KOALABYTE_PI_BLUEZ_NODE"] = "0"
    try:
        election = elect_ble_roles(requested_by="readiness_check")
        command = esp32_role_command(election)
    finally:
        if previous is None:
            os.environ.pop("KOALABYTE_PI_BLUEZ_NODE", None)
        else:
            os.environ["KOALABYTE_PI_BLUEZ_NODE"] = previous

    if election.heltec_role != "primary_ble_controller":
        failures.append("Heltec is not retained as primary BLE controller")
    if election.pi_bluez_role != "unavailable":
        failures.append("forced-disabled Pi BlueZ was not marked unavailable")
    if election.esp32_role != "heltec_fallback_ble_node":
        failures.append("ESP32 was not elected as the Heltec fallback BLE node")
    if command.get("type") != "ble_role" or command.get("role") != "heltec_fallback_ble_node":
        failures.append("ESP32 fallback role command is malformed")

    require_marker(
        ROOT / "firmware/esp32-dualeye/include/config.h",
        "ENABLE_ESP32_BLE_FAILOVER 1",
        failures,
    )
    require_marker(
        ROOT / "firmware/esp32-dualeye/include/config.h",
        "KOALA_BLE_NVS_NAMESPACE",
        failures,
    )
    require_marker(
        ROOT / "firmware/esp32-dualeye/scripts/patch_guarded_ble_failover.py",
        "controller_start_quarantined_after_previous_reset",
        failures,
    )
    require_marker(
        ROOT / "firmware/esp32-dualeye/platformio.ini",
        "patch_guarded_ble_failover.py",
        failures,
    )
    require_marker(
        ROOT / "scripts/run_ble_node_manager_service.sh",
        "KOALABYTE_BLE_MANAGER_OWNS_ESP32:-0",
        failures,
    )
    require_marker(
        PI_ROOT / "koalablue/esp32_dualeye_speech_synced_bridge.py",
        "elect_ble_roles",
        failures,
    )

    payload = {
        "status": "BLE_FAILOVER_READY" if not failures else "BLE_FAILOVER_INCOMPLETE",
        "heltec_primary": True,
        "preferred_node": "raspberry-pi-bluez",
        "fallback_node": "esp32-s3-dualeye",
        "forced_disabled_election": election.to_payload(),
        "esp32_command": command,
        "single_esp32_serial_owner": "koalabyte-dualeye-voice-bridge.service",
        "ble_manager_direct_esp32_ownership": False,
        "esp32_boot_ble_default": "standby",
        "esp32_controller_start": "explicit_pi_role_command_only",
        "persistent_crash_guard": True,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
