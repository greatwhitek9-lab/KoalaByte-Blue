from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .serial_command_bus import socket_path, submit_command

STATUS_PATH = Path(
    os.getenv(
        "KOALABYTE_T114_STATUS_SNAPSHOT",
        "logs/ble_nodes/t114_status_snapshot.json",
    )
)
BLE_EVENTS_PATH = Path(
    os.getenv("KOALABYTE_BLE_EVENTS_PATH", "logs/ble_nodes/ble_events.jsonl")
)
BROKER_WAIT_SECONDS = max(
    0.2, float(os.getenv("KOALABYTE_T114_BROKER_WAIT_SECONDS", "1.2"))
)


def _direct_allowed() -> bool:
    return os.getenv("KOALABYTE_ALLOW_DIRECT_HELTEC_SERIAL", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _socket_ready() -> bool:
    try:
        return stat.S_ISSOCK(socket_path("heltec").stat().st_mode)
    except OSError:
        return False


def _submit_and_wait(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not _socket_ready():
        return _read_json(STATUS_PATH)
    previous = STATUS_PATH.stat().st_mtime_ns if STATUS_PATH.exists() else 0
    delivered = False
    for payload in payloads:
        result = submit_command("heltec", payload, queue_if_unavailable=False)
        delivered = delivered or result.delivered
    if delivered:
        deadline = time.monotonic() + BROKER_WAIT_SECONDS
        while time.monotonic() < deadline:
            try:
                if STATUS_PATH.exists() and STATUS_PATH.stat().st_mtime_ns > previous:
                    break
            except OSError:
                pass
            time.sleep(0.05)
    return _read_json(STATUS_PATH)


def _redacted_events(duration_seconds: int, raw_addresses: bool) -> list[dict[str, Any]]:
    if not BLE_EVENTS_PATH.exists():
        return []
    cutoff = time.time() - max(1, int(duration_seconds))
    rows = BLE_EVENTS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    events: list[dict[str, Any]] = []
    for line in rows[-1000:]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        source = str(event.get("source") or "").lower()
        if not any(token in source for token in ("heltec", "t114", "nrf52840")):
            continue
        stamp = float(event.get("last_seen_ts") or event.get("timestamp") or 0.0)
        if stamp and stamp < cutoff:
            continue
        clean = dict(event)
        if not raw_addresses and clean.get("addr"):
            clean["addr"] = "redacted"
            clean["addr_redacted"] = True
        clean.pop("raw", None)
        events.append(clean)
    return events[-100:]


def _controller_result(
    module: ModuleType,
    *,
    action: str,
    adapter: str,
    output_dir: Path,
    validation_path: Path,
) -> Any:
    started = time.time()
    status = _submit_and_wait(
        [
            {"type": "node_roles"},
            {"type": "ble_status"},
            {"type": "ble_tx_status"},
            {"type": "gnss_status"},
            {"type": "status"},
        ]
    )
    owner_ready = _socket_ready()
    responding = bool(status.get("responding", False))
    selected_port = str(status.get("port") or "")
    checks = [
        module.T114ControllerCheck(
            ["koalabyte-serial-owner", "heltec"],
            0 if owner_ready else 1,
            "owner socket ready" if owner_ready else "",
            "" if owner_ready else "Heltec serial-owner socket is unavailable",
            skipped=False,
            reason=None if owner_ready else "start koalabyte-ble-node-manager.service",
        ),
        module.T114ControllerCheck(
            ["koalabyte-owner-status", str(STATUS_PATH)],
            0 if responding else 1,
            json.dumps(status, sort_keys=True),
            "" if responding else str(status.get("error") or "no fresh T114 response"),
            skipped=False,
            reason=None if responding else "owner has no fresh firmware status",
        ),
    ]
    result = module.T114BluezResult(
        action=action,
        status="ready" if owner_ready and responding else "missing_t114_owner_status",
        started_at=started,
        ended_at=time.time(),
        output_dir=str(output_dir),
        hci_controller_expected=False,
        hci_controller_present=False,
        selected_adapter=adapter,
        selected_port=selected_port,
        controller_mode="combined-safe-owner-broker",
        checks=checks,
        t114_serial_events=[status] if status else [],
        artifacts={
            "status_snapshot": str(STATUS_PATH),
            "validation": str(validation_path),
        },
        safety={
            "exclusive_serial_owner": True,
            "direct_serial_open": False,
            "authorized_lab_use_only": True,
            "pairing_bypass": False,
            "gatt_writes": False,
            "spoofing": False,
            "packet_replay": False,
            "disruptive_actions": False,
        },
        next_steps=(
            []
            if owner_ready and responding
            else [
                "Verify koalabyte-ble-node-manager.service is active.",
                "Verify /dev/koalabyte-heltec exists and the T114 firmware responds.",
            ]
        ),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = output_dir / f"t114_owner_{action}_{int(started)}.json"
    module._write_json(summary, asdict(result))
    module._write_json(validation_path, asdict(result))
    result.artifacts["summary"] = str(summary)
    return result


def install(module: ModuleType) -> None:
    """Replace runtime utility entrypoints while preserving explicit maintenance mode."""

    if getattr(module, "_koalabyte_owner_broker_installed", False):
        return
    original_check: Callable[..., Any] = module.check_controller
    original_run: Callable[..., Any] = module.run_wrapped_bluez

    def check_controller(
        adapter: str = "",
        port: str = "",
        output_dir: Path = module.DEFAULT_OUTPUT_DIR,
        validation_path: Path = module.DEFAULT_VALIDATION_PATH,
        baud: int = module.DEFAULT_BAUD,
    ) -> Any:
        if _direct_allowed():
            return original_check(
                adapter=adapter,
                port=port,
                output_dir=output_dir,
                validation_path=validation_path,
                baud=baud,
            )
        return _controller_result(
            module,
            action="controller-check",
            adapter=adapter,
            output_dir=Path(output_dir),
            validation_path=Path(validation_path),
        )

    def run_wrapped_bluez(
        action: str,
        *,
        adapter: str = "",
        port: str = "",
        duration_seconds: int = 15,
        output_dir: Path = module.DEFAULT_OUTPUT_DIR,
        raw_addresses: bool = False,
        baud: int = module.DEFAULT_BAUD,
        tx_name: str = "KoalaByte Lab",
        confirm_send: bool = False,
    ) -> Any:
        if _direct_allowed():
            return original_run(
                action,
                adapter=adapter,
                port=port,
                duration_seconds=duration_seconds,
                output_dir=output_dir,
                raw_addresses=raw_addresses,
                baud=baud,
                tx_name=tx_name,
                confirm_send=confirm_send,
            )

        started = time.time()
        output = Path(output_dir)
        validation = Path("logs/hardware_validation") / (
            f"t114_owner_{action}_{int(started)}.json"
        )
        if action in {"controller-check", "status", "inventory"}:
            result = _controller_result(
                module,
                action=action,
                adapter=adapter,
                output_dir=output,
                validation_path=validation,
            )
            if action == "inventory":
                result.wrapped_bluez_result = {
                    "owner_socket": str(socket_path("heltec")),
                    "status_snapshot": str(STATUS_PATH),
                    "direct_serial_open": False,
                }
            return result

        if action == "manifest":
            result = _controller_result(
                module,
                action=action,
                adapter=adapter,
                output_dir=output,
                validation_path=validation,
            )
            result.status = "success"
            result.wrapped_bluez_result = module._manifest(output)
            module._write_json(validation, asdict(result))
            return result

        events: list[dict[str, Any]] = []
        status_payload: dict[str, Any] = {}
        result_status = "success"
        if action in {"scan", "monitor", "all-safe"}:
            status_payload = _submit_and_wait(
                [{"type": "node_roles"}, {"type": "ble_status"}]
            )
            events = _redacted_events(duration_seconds, raw_addresses)
            if not _socket_ready():
                result_status = "blocked_missing_t114_owner"
        elif action == "tx-status":
            status_payload = _submit_and_wait([{"type": "ble_tx_status"}])
            events = [status_payload] if status_payload else []
            result_status = (
                "success"
                if status_payload.get("responding")
                else "blocked_or_no_response"
            )
        elif action == "lab-advertise-stop":
            status_payload = _submit_and_wait(
                [
                    {"type": "ble_lab_advertise_stop"},
                    {"type": "ble_tx_status"},
                ]
            )
            events = [status_payload] if status_payload else []
            result_status = (
                "success"
                if status_payload.get("responding")
                else "blocked_or_no_response"
            )
        elif action == "lab-advertise-start":
            if not confirm_send:
                result_status = "blocked_confirmation_required"
                events = [
                    {
                        "type": "ble_tx_status",
                        "status": "blocked",
                        "reason": "confirm_send is required for bounded owned-lab advertising",
                    }
                ]
            else:
                status_payload = _submit_and_wait(
                    [
                        {
                            "type": "ble_lab_advertise_start",
                            "name": tx_name,
                            "duration_ms": max(1, int(duration_seconds)) * 1000,
                            "confirm": True,
                        },
                        {"type": "ble_tx_status"},
                    ]
                )
                events = [status_payload] if status_payload else []
                result_status = (
                    "success"
                    if status_payload.get("responding")
                    else "blocked_or_no_response"
                )
        else:
            raise ValueError(f"Unsupported T114 brokered BLE action: {action}")

        result = module.T114BluezResult(
            action=action,
            status=result_status,
            started_at=started,
            ended_at=time.time(),
            output_dir=str(output),
            hci_controller_expected=False,
            hci_controller_present=False,
            selected_adapter=adapter,
            selected_port=str(status_payload.get("port") or ""),
            controller_mode="combined-safe-owner-broker",
            checks=[],
            wrapped_bluez_result={
                "owner_snapshot": status_payload,
                "ledger_events": events,
                "event_count": len(events),
            },
            t114_serial_events=events,
            artifacts={
                "status_snapshot": str(STATUS_PATH),
                "ble_event_ledger": str(BLE_EVENTS_PATH),
                "validation": str(validation),
            },
            safety={
                "exclusive_serial_owner": True,
                "direct_serial_open": False,
                "authorized_lab_use_only": True,
                "bounded_non_connectable_tx_only": True,
                "confirm_send_required": action == "lab-advertise-start",
                "pairing_bypass": False,
                "gatt_writes": False,
                "spoofing": False,
                "packet_replay": False,
                "disruptive_actions": False,
            },
            next_steps=[],
        )
        output.mkdir(parents=True, exist_ok=True)
        summary = output / f"t114_owner_{action}_{int(started)}.json"
        result.artifacts["summary"] = str(summary)
        module._write_json(summary, asdict(result))
        module._write_json(validation, asdict(result))
        return result

    module.check_controller = check_controller
    module.run_wrapped_bluez = run_wrapped_bluez
    module._koalabyte_owner_broker_installed = True


__all__ = ["install"]
