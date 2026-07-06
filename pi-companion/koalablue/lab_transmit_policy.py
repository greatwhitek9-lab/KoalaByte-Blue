from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

POLICY_PATH = Path("logs/one_shot/lab_transmit_policy.json")
ARM_STATE_PATH = Path("logs/one_shot/lab_transmit_arm_state.json")
RF_BLE_ARM_STATE_PATH = Path("logs/one_shot/rf_ble_lab_arm_state.json")

ALLOWED_LAB_PROFILES = {"owned-lab", "authorized-owned-lab", "bench-only"}
ALLOWED_CAN_MODES = {"gated-bench", "listen-only", "disabled"}
ALLOWED_RF_BLE_MODES = {"gated-lab", "listen-only", "passive-only", "disabled-during-install", "disabled"}

DEFAULT_LAB_PROFILE = "owned-lab"
DEFAULT_CAN_MODE = "gated-bench"
DEFAULT_RF_BLE_MODE = "gated-lab"

CAN_MODE_LABELS = {
    "gated-bench": "Gated synthetic CAN bench transmit is available after menu confirmation.",
    "listen-only": "CAN transmit rows stay blocked; listen/status/report rows remain available.",
    "disabled": "CAN bench transmit and listen-transmit rows stay blocked from the menu.",
}
RF_BLE_MODE_LABELS = {
    "gated-lab": "Gated synthetic RF/BLE lab transmit is available after menu confirmation.",
    "listen-only": "RF/BLE transmit rows stay blocked; listen/capture/status/review rows remain available.",
    "passive-only": "RF/BLE menu workflows stay passive/readiness/review oriented.",
    "disabled-during-install": "RF/BLE live transmit or replay is not performed by installer/menu policy.",
    "disabled": "RF/BLE transmit rows stay blocked from the menu.",
}


def _truthy(value: Any) -> bool:
    return str(value).strip() in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def _env_or_existing(name: str, existing: dict[str, Any], key: str, default: str) -> str:
    return str(os.getenv(name) or existing.get(key) or default)


def normalize_policy(
    *,
    lab_profile: str | None = None,
    can_transmit_mode: str | None = None,
    rf_ble_transmit_mode: str | None = None,
) -> tuple[dict[str, str], list[str]]:
    existing = _read_json(POLICY_PATH)
    profile = lab_profile or _env_or_existing("KOALABYTE_LAB_PROFILE", existing, "lab_profile", DEFAULT_LAB_PROFILE)
    can_mode = can_transmit_mode or _env_or_existing("KOALABYTE_CAN_TRANSMIT_MODE", existing, "can_transmit_mode", DEFAULT_CAN_MODE)
    rf_ble_mode = rf_ble_transmit_mode or _env_or_existing("KOALABYTE_RF_BLE_TRANSMIT_MODE", existing, "rf_ble_transmit_mode", DEFAULT_RF_BLE_MODE)

    errors: list[str] = []
    if profile not in ALLOWED_LAB_PROFILES:
        errors.append(f"Unsupported KOALABYTE_LAB_PROFILE={profile!r}")
    if can_mode not in ALLOWED_CAN_MODES:
        errors.append(f"Unsupported KOALABYTE_CAN_TRANSMIT_MODE={can_mode!r}")
    if rf_ble_mode not in ALLOWED_RF_BLE_MODES:
        errors.append(f"Unsupported KOALABYTE_RF_BLE_TRANSMIT_MODE={rf_ble_mode!r}")
    return {"lab_profile": profile, "can_transmit_mode": can_mode, "rf_ble_transmit_mode": rf_ble_mode}, errors


def write_policy(
    *,
    lab_profile: str | None = None,
    can_transmit_mode: str | None = None,
    rf_ble_transmit_mode: str | None = None,
    source: str = "menu",
) -> dict[str, Any]:
    policy, errors = normalize_policy(lab_profile=lab_profile, can_transmit_mode=can_transmit_mode, rf_ble_transmit_mode=rf_ble_transmit_mode)
    can_mode = policy["can_transmit_mode"]
    rf_ble_mode = policy["rf_ble_transmit_mode"]
    payload: dict[str, Any] = {
        "status": "LAB_TRANSMIT_POLICY_OK" if not errors else "LAB_TRANSMIT_POLICY_ERROR",
        **policy,
        "source": source,
        "menu_actionable": True,
        "installer_transmits_during_setup": False,
        "can_policy": {
            "mode": can_mode,
            "description": CAN_MODE_LABELS.get(can_mode, "unknown"),
            "allowed_path": "isolated SocketCAN bench simulator only after selecting Bench Simulator Confirm ON from Koala Kan Kommander",
            "menu_arm_required": True,
            "no_automatic_vehicle_writes": True,
            "no_dtc_clear_or_ecu_coding": True,
            "no_captured_traffic_replay": True,
        },
        "rf_ble_policy": {
            "mode": rf_ble_mode,
            "description": RF_BLE_MODE_LABELS.get(rf_ble_mode, "unknown"),
            "allowed_path": "synthetic owned-lab BLE/RF advertisement/test payload only after selecting RF/BLE Lab Confirm ON from Koala Kapture or Koala Kry",
            "menu_arm_required": True,
            "installer_live_transmit": False,
            "menu_live_replay": False,
            "no_pairing_or_writes_during_install": True,
            "no_replay_during_install": True,
            "no_captured_signal_replay": True,
        },
        "permitted_menu_actions": [
            "koala_kan_generate_payloads",
            "koala_kan_transmit_placeholder",
            "lab_transmit_bench_arm_on",
            "lab_transmit_bench_arm_off",
            "koala_kan_transmit_gate",
            "koala_kan_listen_transmit_gate",
            "koala_kapture_listen_gate",
            "koala_kapture_transmit_placeholder",
            "koala_kapture_transmit_gate",
            "koala_kapture_listen_transmit_gate",
            "koala_kry_listen_gate",
            "koala_kry_transmit_placeholder",
            "koala_kry_transmit_gate",
            "koala_kry_listen_transmit_gate",
        ],
        "errors": errors,
        "updated_at": time.time(),
    }
    if can_mode != "gated-bench":
        set_bench_arm(False, source=f"{source}:can-mode-{can_mode}", write_policy_first=False)
    if rf_ble_mode != "gated-lab":
        set_rf_ble_arm(False, source=f"{source}:rf-ble-mode-{rf_ble_mode}", write_policy_first=False)
    os.environ["KOALABYTE_LAB_PROFILE"] = policy["lab_profile"]
    os.environ["KOALABYTE_CAN_TRANSMIT_MODE"] = can_mode
    os.environ["KOALABYTE_RF_BLE_TRANSMIT_MODE"] = rf_ble_mode
    return _write_json(POLICY_PATH, payload)


def policy_status() -> dict[str, Any]:
    payload = write_policy(source="menu-status")
    arm = arm_status()
    rf_ble_arm = rf_ble_arm_status()
    payload["bench_arm_state"] = arm
    payload["rf_ble_arm_state"] = rf_ble_arm
    payload["can_transmit_gate"] = can_transmit_gate_status()
    payload["rf_ble_transmit_gate"] = rf_ble_transmit_gate_status()
    return payload


def set_can_mode(mode: str) -> dict[str, Any]:
    if mode not in ALLOWED_CAN_MODES:
        return {"status": "LAB_TRANSMIT_POLICY_ERROR", "error": f"unsupported CAN mode: {mode}", "allowed": sorted(ALLOWED_CAN_MODES)}
    return write_policy(can_transmit_mode=mode, source=f"menu:set-can-{mode}")


def set_rf_ble_mode(mode: str) -> dict[str, Any]:
    if mode not in ALLOWED_RF_BLE_MODES:
        return {"status": "LAB_TRANSMIT_POLICY_ERROR", "error": f"unsupported RF/BLE mode: {mode}", "allowed": sorted(ALLOWED_RF_BLE_MODES)}
    return write_policy(rf_ble_transmit_mode=mode, source=f"menu:set-rf-ble-{mode}")


def set_bench_arm(armed: bool, *, source: str = "menu", write_policy_first: bool = True) -> dict[str, Any]:
    if write_policy_first:
        policy = write_policy(source=f"{source}:arm-policy-check")
    else:
        policy = _read_json(POLICY_PATH) or normalize_policy()[0]
    can_mode = str(policy.get("can_transmit_mode", DEFAULT_CAN_MODE))
    allowed_to_arm = armed and can_mode == "gated-bench" and not policy.get("errors")
    bench_simulator = bool(allowed_to_arm)
    confirm_transmit = bool(allowed_to_arm)
    os.environ["KOALABYTE_CAN_BENCH_SIMULATOR"] = "1" if bench_simulator else "0"
    os.environ["KOALABYTE_CAN_CONFIRM_TRANSMIT"] = "1" if confirm_transmit else "0"
    payload = {
        "status": "LAB_TRANSMIT_BENCH_ARMED" if allowed_to_arm else "LAB_TRANSMIT_BENCH_DISARMED",
        "requested_armed": armed,
        "bench_simulator_confirmed": bench_simulator,
        "explicit_transmit_confirmation": confirm_transmit,
        "can_transmit_mode": can_mode,
        "source": source,
        "operator_confirmation": "menu row selected" if armed else "disarmed from menu or policy",
        "note": "Only select Bench Transmit Gate while connected to an isolated owned bench simulator.",
        "updated_at": time.time(),
    }
    return _write_json(ARM_STATE_PATH, payload)


def set_rf_ble_arm(armed: bool, *, source: str = "menu", write_policy_first: bool = True) -> dict[str, Any]:
    if write_policy_first:
        policy = write_policy(source=f"{source}:rf-ble-arm-policy-check")
    else:
        policy = _read_json(POLICY_PATH) or normalize_policy()[0]
    rf_ble_mode = str(policy.get("rf_ble_transmit_mode", DEFAULT_RF_BLE_MODE))
    allowed_to_arm = armed and rf_ble_mode == "gated-lab" and not policy.get("errors")
    lab_fixture_confirmed = bool(allowed_to_arm)
    confirm_transmit = bool(allowed_to_arm)
    os.environ["KOALABYTE_RF_BLE_LAB_FIXTURE"] = "1" if lab_fixture_confirmed else "0"
    os.environ["KOALABYTE_RF_BLE_CONFIRM_TRANSMIT"] = "1" if confirm_transmit else "0"
    payload = {
        "status": "RF_BLE_LAB_TRANSMIT_ARMED" if allowed_to_arm else "RF_BLE_LAB_TRANSMIT_DISARMED",
        "requested_armed": armed,
        "lab_fixture_confirmed": lab_fixture_confirmed,
        "explicit_transmit_confirmation": confirm_transmit,
        "rf_ble_transmit_mode": rf_ble_mode,
        "source": source,
        "operator_confirmation": "menu row selected" if armed else "disarmed from menu or policy",
        "note": "Only select RF/BLE Transmit Gate inside an owned, isolated lab fixture using synthetic payloads. Captured signal replay stays blocked.",
        "updated_at": time.time(),
    }
    return _write_json(RF_BLE_ARM_STATE_PATH, payload)


def arm_status() -> dict[str, Any]:
    state = _read_json(ARM_STATE_PATH)
    return {
        "status": state.get("status", "LAB_TRANSMIT_BENCH_DISARMED"),
        "bench_simulator_confirmed": _truthy(os.getenv("KOALABYTE_CAN_BENCH_SIMULATOR", state.get("bench_simulator_confirmed", False))),
        "explicit_transmit_confirmation": _truthy(os.getenv("KOALABYTE_CAN_CONFIRM_TRANSMIT", state.get("explicit_transmit_confirmation", False))),
        "can_transmit_mode": str(state.get("can_transmit_mode") or (_read_json(POLICY_PATH).get("can_transmit_mode", DEFAULT_CAN_MODE))),
        "artifact_path": str(ARM_STATE_PATH),
    }


def rf_ble_arm_status() -> dict[str, Any]:
    state = _read_json(RF_BLE_ARM_STATE_PATH)
    return {
        "status": state.get("status", "RF_BLE_LAB_TRANSMIT_DISARMED"),
        "lab_fixture_confirmed": _truthy(os.getenv("KOALABYTE_RF_BLE_LAB_FIXTURE", state.get("lab_fixture_confirmed", False))),
        "explicit_transmit_confirmation": _truthy(os.getenv("KOALABYTE_RF_BLE_CONFIRM_TRANSMIT", state.get("explicit_transmit_confirmation", False))),
        "rf_ble_transmit_mode": str(state.get("rf_ble_transmit_mode") or (_read_json(POLICY_PATH).get("rf_ble_transmit_mode", DEFAULT_RF_BLE_MODE))),
        "artifact_path": str(RF_BLE_ARM_STATE_PATH),
    }


def can_transmit_gate_status() -> dict[str, Any]:
    policy = _read_json(POLICY_PATH) or write_policy(source="gate-status")
    arm = arm_status()
    can_mode = str(policy.get("can_transmit_mode", DEFAULT_CAN_MODE))
    allowed = can_mode == "gated-bench" and bool(arm["bench_simulator_confirmed"]) and bool(arm["explicit_transmit_confirmation"])
    reason = "menu bench simulator confirmation is armed" if allowed else "select CAN Mode: Gated Bench and Bench Simulator Confirm ON before bench transmit"
    if can_mode != "gated-bench":
        reason = f"CAN transmit mode is {can_mode}; bench transmit stays blocked"
    return {
        "allowed": allowed,
        "reason": reason,
        "can_transmit_mode": can_mode,
        "bench_simulator_confirmed": bool(arm["bench_simulator_confirmed"]),
        "explicit_transmit_confirmation": bool(arm["explicit_transmit_confirmation"]),
        "policy_path": str(POLICY_PATH),
        "arm_state_path": str(ARM_STATE_PATH),
    }


def rf_ble_transmit_gate_status() -> dict[str, Any]:
    policy = _read_json(POLICY_PATH) or write_policy(source="rf-ble-gate-status")
    arm = rf_ble_arm_status()
    rf_ble_mode = str(policy.get("rf_ble_transmit_mode", DEFAULT_RF_BLE_MODE))
    allowed = rf_ble_mode == "gated-lab" and bool(arm["lab_fixture_confirmed"]) and bool(arm["explicit_transmit_confirmation"])
    reason = "menu RF/BLE lab fixture confirmation is armed" if allowed else "select RF/BLE Mode: Gated Lab and RF/BLE Lab Confirm ON before transmit"
    if rf_ble_mode != "gated-lab":
        reason = f"RF/BLE transmit mode is {rf_ble_mode}; transmit stays blocked"
    return {
        "allowed": allowed,
        "reason": reason,
        "rf_ble_transmit_mode": rf_ble_mode,
        "lab_fixture_confirmed": bool(arm["lab_fixture_confirmed"]),
        "explicit_transmit_confirmation": bool(arm["explicit_transmit_confirmation"]),
        "policy_path": str(POLICY_PATH),
        "arm_state_path": str(RF_BLE_ARM_STATE_PATH),
        "no_captured_signal_replay": True,
    }


def blocked_transmit_action(command: str, gate: dict[str, Any] | None = None) -> dict[str, Any]:
    gate_payload = gate or can_transmit_gate_status()
    payload = {
        "status": "blocked",
        "command": command,
        "reason": gate_payload.get("reason", "bench transmit gate is not armed"),
        "can_transmit_gate": gate_payload,
        "frames_requested": [],
        "frames_sent": [],
        "safety_scope": {
            "allowed": "Synthetic lab payloads to an isolated owned bench simulator only.",
            "excluded": [
                "No UDS, OBD, DTC, ECU coding, security access, or actuator-oriented payloads.",
                "No vehicle, battery, industrial controller, OEM arbitration ID, or captured traffic replay use.",
            ],
        },
        "timestamp": time.time(),
    }
    out = Path("logs/koala_kan_kommander")
    out.mkdir(parents=True, exist_ok=True)
    artifact = out / f"{command}_blocked_by_menu_gate_{int(time.time())}.json"
    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["artifact_path"] = str(artifact)
    return payload


def blocked_rf_ble_action(command: str, gate: dict[str, Any] | None = None) -> dict[str, Any]:
    gate_payload = gate or rf_ble_transmit_gate_status()
    payload = {
        "status": "blocked",
        "command": command,
        "reason": gate_payload.get("reason", "RF/BLE transmit gate is not armed"),
        "rf_ble_transmit_gate": gate_payload,
        "payloads_requested": [],
        "payloads_sent": [],
        "safety_scope": {
            "allowed": "Synthetic owned-lab RF/BLE advertisement/test payloads inside an isolated lab fixture only.",
            "excluded": [
                "No captured Bluetooth/RF signal replay.",
                "No rebroadcasting captured identifiers or payloads.",
                "No pairing, GATT writes, connection attempts, disruption, impersonation, or jamming.",
            ],
        },
        "timestamp": time.time(),
    }
    out = Path("logs/rf_ble_lab_transmit")
    out.mkdir(parents=True, exist_ok=True)
    artifact = out / f"{command}_blocked_by_menu_gate_{int(time.time())}.json"
    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["artifact_path"] = str(artifact)
    return payload


def run_menu_action(command: str) -> dict[str, Any]:
    handlers = {
        "lab_transmit_policy_status": policy_status,
        "lab_transmit_can_gated_bench": lambda: set_can_mode("gated-bench"),
        "lab_transmit_can_listen_only": lambda: set_can_mode("listen-only"),
        "lab_transmit_can_disabled": lambda: set_can_mode("disabled"),
        "lab_transmit_rf_ble_gated_lab": lambda: set_rf_ble_mode("gated-lab"),
        "lab_transmit_rf_ble_listen_only": lambda: set_rf_ble_mode("listen-only"),
        "lab_transmit_rf_ble_passive_only": lambda: set_rf_ble_mode("passive-only"),
        "lab_transmit_rf_ble_disabled_install": lambda: set_rf_ble_mode("disabled-during-install"),
        "lab_transmit_rf_ble_disabled": lambda: set_rf_ble_mode("disabled"),
        "lab_transmit_bench_arm_on": lambda: set_bench_arm(True, source="menu:bench-arm-on"),
        "lab_transmit_bench_arm_off": lambda: set_bench_arm(False, source="menu:bench-arm-off"),
        "lab_transmit_rf_ble_arm_on": lambda: set_rf_ble_arm(True, source="menu:rf-ble-arm-on"),
        "lab_transmit_rf_ble_arm_off": lambda: set_rf_ble_arm(False, source="menu:rf-ble-arm-off"),
    }
    handler = handlers.get(command)
    if handler is None:
        return {"status": "LAB_TRANSMIT_ACTION_RECORDED", "command": command, "policy": policy_status()}
    return handler()
