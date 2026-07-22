from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Optional

from .serial_command_bus import socket_path, submit_command

ESP32_EVENTS_PATH = Path(
    os.getenv("KOALABYTE_NODE_EVENTS_PATH", "logs/runtime/node_events.jsonl")
)
HELTEC_EVENTS_PATH = Path(
    os.getenv("KOALABYTE_BLE_EVENTS_PATH", "logs/ble_nodes/ble_events.jsonl")
)
MAX_LEDGER_LINES = max(
    100, min(int(os.getenv("KOALA_KOMBAT_MAX_LEDGER_LINES", "4000")), 20000)
)
MAX_BROKER_SCAN_SECONDS = max(
    1.0, min(float(os.getenv("KOALA_KOMBAT_MAX_BROKER_SCAN_SECONDS", "20")), 60.0)
)


def _socket_ready(target: str) -> bool:
    try:
        return stat.S_ISSOCK(socket_path(target).stat().st_mode)
    except OSError:
        return False


def _event_timestamp(event: dict[str, Any]) -> float:
    for key in (
        "received_at",
        "last_seen_ts",
        "first_seen_ts",
        "timestamp",
        "ts",
        "updated_at",
    ):
        value = event.get(key)
        try:
            if value not in {None, ""}:
                return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _read_jsonl_since(path: Path, cutoff: float) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines[-MAX_LEDGER_LINES:]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        timestamp = _event_timestamp(payload)
        if timestamp and timestamp < cutoff:
            continue
        events.append(payload)
    return events


def _logical_owner_endpoints() -> dict[str, str]:
    return {
        "esp32": str(socket_path("esp32")),
        "heltec": str(socket_path("heltec")),
    }


def _request_owner_scan(
    *, include_wifi: bool, include_ble: bool, notes: list[str]
) -> dict[str, bool]:
    owners = {
        "esp32": _socket_ready("esp32"),
        "heltec": _socket_ready("heltec"),
    }
    if owners["esp32"]:
        result = submit_command(
            "esp32",
            {
                "type": "scan_nodes",
                "wifi": bool(include_wifi),
                "ble": bool(include_ble),
                "source": "koala-kombat-kruisin",
                "passive_only": True,
            },
            queue_if_unavailable=False,
        )
        if not result.delivered:
            notes.append(f"ESP32 owner scan request was not delivered: {result.status}")
    else:
        notes.append("ESP32 serial owner is unavailable; secondary node scan skipped")

    if owners["heltec"] and include_ble:
        for payload in (
            {"type": "node_roles"},
            {"type": "ble_status"},
            {"type": "ble_tx_status"},
        ):
            result = submit_command(
                "heltec",
                {
                    **payload,
                    "source": "koala-kombat-kruisin",
                    "passive_only": True,
                },
                queue_if_unavailable=False,
            )
            if not result.delivered:
                notes.append(
                    f"Heltec owner status request was not delivered: {result.status}"
                )
                break
    elif include_ble:
        notes.append("Heltec serial owner is unavailable; primary BLE ledger may be stale")
    return owners


def _normalise_redacted_identifier(event: dict[str, Any]) -> dict[str, Any]:
    clean = dict(event)
    for key in ("bssid", "addr", "address", "mac"):
        value = str(clean.get(key) or "").strip()
        fingerprint = str(clean.get(f"{key}_fingerprint") or "").strip()
        if (not value or value.lower() == "redacted") and fingerprint:
            clean[key] = f"hash:{fingerprint}"
            clean["identifier_is_fingerprint"] = True
    return clean


def install(module: ModuleType) -> None:
    """Route Koala Kombat node surveys through the existing serial owners."""

    if getattr(module, "_koalabyte_owner_broker_installed", False):
        return

    original_event_to_record: Callable[..., Optional[Any]] = (
        module._node_event_to_record
    )

    def owner_ports() -> dict[str, str]:
        return _logical_owner_endpoints()

    def event_to_record(
        event: dict[str, Any],
        fix: Optional[dict[str, object]],
        *,
        include_wifi: bool,
        include_ble: bool,
    ) -> Optional[Any]:
        return original_event_to_record(
            _normalise_redacted_identifier(event),
            fix,
            include_wifi=include_wifi,
            include_ble=include_ble,
        )

    def read_owner_events(
        *,
        duration_seconds: float,
        include_wifi: bool,
        include_ble: bool,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        if not module._truthy(os.getenv(module.NODE_ENABLE_ENV), default=True):
            return [], [f"node mesh disabled by {module.NODE_ENABLE_ENV}=0"]

        notes: list[str] = []
        started = time.time()
        owners = _request_owner_scan(
            include_wifi=include_wifi,
            include_ble=include_ble,
            notes=notes,
        )
        if not any(owners.values()):
            return [], notes

        wait_seconds = min(
            max(1.0, float(duration_seconds)), MAX_BROKER_SCAN_SECONDS
        )
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            time.sleep(min(0.2, max(0.01, deadline - time.monotonic())))

        cutoff = started - 1.0
        events: list[dict[str, Any]] = []
        if owners["esp32"]:
            for payload in _read_jsonl_since(ESP32_EVENTS_PATH, cutoff):
                event_type = str(payload.get("type") or "")
                if include_wifi and event_type in {
                    "wifi_ap_seen",
                    "wifi_seen",
                    "ap_seen",
                }:
                    events.append(payload)
                elif include_ble and event_type in {
                    "ble_adv_seen",
                    "ble_seen",
                    "advertisement",
                }:
                    events.append(payload)
        if include_ble:
            for payload in _read_jsonl_since(HELTEC_EVENTS_PATH, cutoff):
                event_type = str(payload.get("type") or "")
                if event_type not in {
                    "ble_adv_seen",
                    "ble_seen",
                    "advertisement",
                }:
                    continue
                source = str(payload.get("source") or "")
                if source:
                    payload = dict(payload)
                    payload.setdefault("node", source)
                events.append(payload)

        if not events:
            notes.append(
                "Serial owners responded, but no new passive node observations were recorded during the scan window"
            )
        notes.append(
            "Koala Kombat used owner sockets and bounded ledgers; no serial tty was opened"
        )
        return events, notes

    module._node_ports = owner_ports
    module._node_event_to_record = event_to_record
    module._read_serial_node_events = read_owner_events
    module._koalabyte_owner_broker_installed = True


__all__ = ["install"]
