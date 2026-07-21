#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue import menu_action_runner  # noqa: E402
from koalablue import rf_ble_lab_gates as gates  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    calls: list[dict[str, Any]] = []
    original_gate = gates._gate_status
    original_t114 = gates._t114_action
    original_capture = gates._capture_pass
    original_set_input = gates._set_kry_input
    original_review = gates._run_kry_review

    def fake_t114(action: str, *, name: str = "", duration_seconds: int = 12, confirm_send: bool = False) -> dict[str, Any]:
        calls.append({
            "action": action,
            "name": name,
            "duration_seconds": duration_seconds,
            "confirm_send": confirm_send,
        })
        if action == "lab-advertise-start":
            return {
                "status": "success",
                "t114_serial_events": [{
                    "type": "ble_tx_status",
                    "status": "started",
                    "non_connectable": True,
                    "owned_lab_only": True,
                }],
            }
        return {
            "status": "success",
            "t114_serial_events": [{
                "type": "ble_tx_status",
                "status": "stopped",
                "non_connectable": True,
                "owned_lab_only": True,
            }],
        }

    fake_capture = {
        "action": "Koala Kapture",
        "records": 3,
        "jsonl_path": "/blecaptures/koala_kapture/test.jsonl",
        "csv_path": "/blecaptures/koala_kapture/test.csv",
        "manifest_path": "/blecaptures/koala_kapture/test_manifest.json",
    }

    try:
        gates._t114_action = fake_t114
        gates._capture_pass = lambda: dict(fake_capture)
        gates._set_kry_input = lambda capture: {
            "status": "KOALA_KRY_CAPTURE_SELECTED",
            "input_path": capture["jsonl_path"],
        }
        gates._run_kry_review = lambda: {
            "status": "KOALA_KRY_REPLAY_COMPLETE",
            "review_only": True,
            "rf_transmission": False,
        }

        gates._gate_status = lambda: {
            "allowed": False,
            "reason": "select RF/BLE Mode: Gated Lab and RF/BLE Lab Confirm ON before transmit",
            "rf_ble_transmit_mode": "listen-only",
        }
        blocked = gates.run_gate_command(gates.KAPTURE_TRANSMIT)
        require(blocked.get("status") == "blocked", "Kapture transmit must fail closed while the gate is off")
        require(not calls, "Blocked transmit must not call the T114 backend")

        gates._gate_status = lambda: {
            "allowed": True,
            "reason": "menu RF/BLE lab fixture confirmation is armed",
            "rf_ble_transmit_mode": "gated-lab",
            "lab_fixture_confirmed": True,
            "explicit_transmit_confirmation": True,
        }

        kapture_tx = gates.run_gate_command(gates.KAPTURE_TRANSMIT)
        require(kapture_tx.get("status") == "RF_BLE_LAB_TRANSMIT_STARTED", "Kapture transmit gate did not start")
        require(kapture_tx.get("rf_ble_transmit_performed") is True, "Kapture transmit gate did not report RF activity")
        require(kapture_tx.get("advertised_name") == gates.KAPTURE_TX_NAME, "Kapture must use its fixed synthetic name")
        require(kapture_tx.get("non_connectable") is True, "Kapture advertisement must be non-connectable")
        require(kapture_tx.get("captured_signal_replay") is False, "Captured signal replay must remain blocked")
        require(calls[-1]["action"] == "lab-advertise-start", "Kapture did not call the T114 advertise backend")
        require(calls[-1]["confirm_send"] is True, "T114 start must include explicit confirmation")
        require(2 <= int(calls[-1]["duration_seconds"]) <= 30, "T114 start duration is not bounded")

        calls.clear()
        kapture_combo = gates.run_gate_command(gates.KAPTURE_LISTEN_TRANSMIT)
        require(kapture_combo.get("status") == "KOALA_KAPTURE_LISTEN_TRANSMIT_COMPLETE", "Kapture combined gate did not complete")
        require(kapture_combo.get("capture", {}).get("records") == 3, "Kapture combined gate did not perform passive capture")
        require([call["action"] for call in calls] == ["lab-advertise-start", "lab-advertise-stop"], "Kapture combined gate must start and stop the bounded beacon")
        require(kapture_combo.get("rf_ble_live_transmit") is False, "Combined gate must be stopped before returning")

        calls.clear()
        kry_combo = gates.run_gate_command(gates.KRY_LISTEN_TRANSMIT)
        require(kry_combo.get("status") == "KOALA_KRY_LISTEN_TRANSMIT_COMPLETE", "Kry combined gate did not complete")
        require(kry_combo.get("kry_input", {}).get("input_path") == fake_capture["jsonl_path"], "Kry did not select the new capture")
        require(kry_combo.get("kry_review", {}).get("review_only") is True, "Kry did not run offline metadata review")
        require(kry_combo.get("captured_identifier_rebroadcast") is False, "Kry must not rebroadcast captured identifiers")
        require([call["action"] for call in calls] == ["lab-advertise-start", "lab-advertise-stop"], "Kry combined gate must start and stop the bounded beacon")
        require(calls[0]["name"] == gates.KRY_TX_NAME, "Kry must use its fixed synthetic name")

        require(gates.KAPTURE_TRANSMIT in gates.ACTIVE_GATE_COMMANDS, "Kapture transmit route is not installed")
        require(gates.KRY_TRANSMIT in gates.ACTIVE_GATE_COMMANDS, "Kry transmit route is not installed")
        require("koala_kapture_transmit_placeholder" not in gates.ACTIVE_GATE_COMMANDS, "Safety-check placeholder must never transmit")
        require(getattr(menu_action_runner, "_koalabyte_rf_ble_lab_gates_installed", False), "Menu action patch was not installed")

        payload = {
            "status": "RF_BLE_LAB_GATES_READY",
            "active_commands": sorted(gates.ACTIVE_GATE_COMMANDS),
            "synthetic_names": [gates.KAPTURE_TX_NAME, gates.KRY_TX_NAME],
            "captured_signal_replay": False,
            "captured_identifier_rebroadcast": False,
            "non_connectable": True,
            "bounded_seconds_max": 30,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    finally:
        gates._gate_status = original_gate
        gates._t114_action = original_t114
        gates._capture_pass = original_capture
        gates._set_kry_input = original_set_input
        gates._run_kry_review = original_review


if __name__ == "__main__":
    raise SystemExit(main())
