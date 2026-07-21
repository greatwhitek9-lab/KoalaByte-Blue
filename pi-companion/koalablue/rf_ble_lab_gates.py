from __future__ import annotations

import asyncio
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable


KAPTURE_LISTEN = "koala_kapture_listen_gate"
KAPTURE_TRANSMIT = "koala_kapture_transmit_gate"
KAPTURE_LISTEN_TRANSMIT = "koala_kapture_listen_transmit_gate"
KRY_LISTEN = "koala_kry_listen_gate"
KRY_TRANSMIT = "koala_kry_transmit_gate"
KRY_LISTEN_TRANSMIT = "koala_kry_listen_transmit_gate"

ACTIVE_GATE_COMMANDS = {
    KAPTURE_LISTEN,
    KAPTURE_TRANSMIT,
    KAPTURE_LISTEN_TRANSMIT,
    KRY_LISTEN,
    KRY_TRANSMIT,
    KRY_LISTEN_TRANSMIT,
}

KAPTURE_TX_NAME = "KoalaByte-Kapture"
KRY_TX_NAME = "KoalaByte-Kry"
DEFAULT_CAPTURE_DIR = "/blecaptures/koala_kapture"


def _bounded_seconds(env_name: str, default: float, minimum: float = 2.0, maximum: float = 30.0) -> float:
    try:
        value = float(os.getenv(env_name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _capture_seconds() -> float:
    return _bounded_seconds("KOALABYTE_MENU_KAPTURE_SECONDS", 12.0)


def _transmit_seconds() -> int:
    return int(_bounded_seconds("KOALABYTE_RF_BLE_LAB_TX_SECONDS", 12.0, minimum=2.0, maximum=30.0))


def _gate_status() -> dict[str, Any]:
    from . import lab_transmit_policy

    return lab_transmit_policy.rf_ble_transmit_gate_status()


def _blocked(command: str, gate: dict[str, Any]) -> dict[str, Any]:
    from . import lab_transmit_policy

    return lab_transmit_policy.blocked_rf_ble_action(command, gate)


def _t114_action(action: str, *, name: str = "", duration_seconds: int = 12, confirm_send: bool = False) -> dict[str, Any]:
    from .t114_bluez import run_wrapped_bluez

    result = run_wrapped_bluez(
        action,
        duration_seconds=duration_seconds,
        output_dir=Path("logs/rf_ble_lab_transmit/t114"),
        tx_name=name or "KoalaByte Lab",
        confirm_send=confirm_send,
    )
    return asdict(result)


def _capture_pass() -> dict[str, Any]:
    from .koala_kapture import KoalaKaptureConfig, KoalaKaptureRecorder

    seconds = _capture_seconds()
    config = KoalaKaptureConfig(
        output_dir=os.getenv("KOALABYTE_KAPTURE_OUTPUT_DIR", DEFAULT_CAPTURE_DIR),
        duration_seconds=seconds,
        scan_window_seconds=min(4.0, seconds),
        max_records=max(1, int(os.getenv("KOALABYTE_MENU_KAPTURE_MAX_RECORDS", "300"))),
    )
    return asdict(asyncio.run(KoalaKaptureRecorder(config).record()))


def _set_kry_input(capture: dict[str, Any]) -> dict[str, Any]:
    from . import koala_kry

    path = str(capture.get("jsonl_path", ""))
    state = koala_kry.load_prompt_state()
    state["input_path"] = path
    saved = koala_kry.save_prompt_state(state)
    return {
        "status": "KOALA_KRY_CAPTURE_SELECTED" if path else "KOALA_KRY_CAPTURE_MISSING",
        "input_path": path,
        **saved,
    }


def _run_kry_review() -> dict[str, Any]:
    from . import koala_kry

    # review_only still performs Koala Kry's local metadata replay, but guarantees
    # that the RF bench review artifact is written. It never retransmits captured
    # identifiers, manufacturer data, service data, addresses, or packet timing.
    return koala_kry.run_from_prompt(review_only=True)


def _tx_started(payload: dict[str, Any]) -> bool:
    if str(payload.get("status", "")) != "success":
        return False
    events = payload.get("t114_serial_events", [])
    return any(
        isinstance(event, dict)
        and event.get("type") == "ble_tx_status"
        and event.get("status") == "started"
        and bool(event.get("non_connectable", True))
        for event in events if isinstance(events, list)
    )


def _start_synthetic_beacon(command: str, name: str) -> dict[str, Any]:
    gate = _gate_status()
    if not gate.get("allowed"):
        return _blocked(command, gate)

    seconds = _transmit_seconds()
    backend = _t114_action(
        "lab-advertise-start",
        name=name,
        duration_seconds=seconds,
        confirm_send=True,
    )
    started = _tx_started(backend)
    return {
        "status": "RF_BLE_LAB_TRANSMIT_STARTED" if started else "RF_BLE_LAB_TRANSMIT_FAILED",
        "command": command,
        "rf_ble_transmit_performed": started,
        "rf_ble_live_transmit": started,
        "synthetic_payload_only": True,
        "non_connectable": True,
        "bounded_duration_seconds": seconds,
        "advertised_name": name,
        "captured_signal_replay": False,
        "captured_identifier_rebroadcast": False,
        "pairing": False,
        "gatt_writes": False,
        "connection_attempts": False,
        "disruption": False,
        "rf_ble_transmit_gate": gate,
        "t114_backend": backend,
    }


def _stop_synthetic_beacon() -> dict[str, Any]:
    return _t114_action("lab-advertise-stop", duration_seconds=2, confirm_send=False)


def _listen_only(command: str, *, kry_input: bool = False) -> dict[str, Any]:
    capture = _capture_pass()
    payload: dict[str, Any] = {
        "status": "KOALA_KRY_LISTEN_COMPLETE" if kry_input else "KOALA_KAPTURE_LISTEN_COMPLETE",
        "command": command,
        "capture": capture,
        "rf_ble_transmit_performed": False,
        "rf_ble_live_transmit": False,
        "captured_signal_replay": False,
    }
    if kry_input:
        payload["kry_input"] = _set_kry_input(capture)
    return payload


def _transmit_only(command: str, *, name: str) -> dict[str, Any]:
    return _start_synthetic_beacon(command, name)


def _listen_transmit(command: str, *, name: str, run_kry: bool = False) -> dict[str, Any]:
    transmit = _start_synthetic_beacon(command, name)
    if not transmit.get("rf_ble_transmit_performed"):
        return transmit

    capture: dict[str, Any] = {}
    kry_input: dict[str, Any] | None = None
    kry_review: dict[str, Any] | None = None
    stop: dict[str, Any] = {}
    try:
        capture = _capture_pass()
        if run_kry:
            kry_input = _set_kry_input(capture)
            kry_review = _run_kry_review()
    finally:
        stop = _stop_synthetic_beacon()

    return {
        "status": "KOALA_KRY_LISTEN_TRANSMIT_COMPLETE" if run_kry else "KOALA_KAPTURE_LISTEN_TRANSMIT_COMPLETE",
        "command": command,
        "transmit": transmit,
        "capture": capture,
        "kry_input": kry_input,
        "kry_review": kry_review,
        "stop": stop,
        "rf_ble_transmit_performed": True,
        "rf_ble_live_transmit": False,
        "synthetic_payload_only": True,
        "captured_signal_replay": False,
        "captured_identifier_rebroadcast": False,
        "pairing": False,
        "gatt_writes": False,
        "connection_attempts": False,
        "disruption": False,
    }


def run_gate_command(command: str) -> dict[str, Any]:
    handlers: dict[str, Callable[[], dict[str, Any]]] = {
        KAPTURE_LISTEN: lambda: _listen_only(command),
        KAPTURE_TRANSMIT: lambda: _transmit_only(command, name=KAPTURE_TX_NAME),
        KAPTURE_LISTEN_TRANSMIT: lambda: _listen_transmit(command, name=KAPTURE_TX_NAME),
        KRY_LISTEN: lambda: _listen_only(command, kry_input=True),
        KRY_TRANSMIT: lambda: _transmit_only(command, name=KRY_TX_NAME),
        KRY_LISTEN_TRANSMIT: lambda: _listen_transmit(command, name=KRY_TX_NAME, run_kry=True),
    }
    handler = handlers.get(command)
    if handler is None:
        raise ValueError(f"Unsupported RF/BLE lab gate command: {command}")
    return handler()


def install_rf_ble_lab_gates() -> None:
    from . import menu_action_runner

    if getattr(menu_action_runner, "_koalabyte_rf_ble_lab_gates_installed", False):
        return

    original = menu_action_runner.run_automated_menu_action

    def routed(command: str, label: str = "", group: str = "") -> dict[str, Any]:
        if command not in ACTIVE_GATE_COMMANDS:
            return original(command, label, group)
        try:
            return menu_action_runner._ok(command, label, run_gate_command(command))
        except Exception as exc:
            return menu_action_runner._error(command, label, exc)

    routed.__name__ = "run_automated_menu_action_with_rf_ble_lab_gates"
    routed.__doc__ = "Route armed Kapture/Kry gate commands to the bounded T114 lab beacon backend."
    menu_action_runner.run_automated_menu_action = routed
    menu_action_runner._koalabyte_rf_ble_lab_gates_installed = True
