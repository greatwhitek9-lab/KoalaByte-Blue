from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .serial_command_bus import socket_path, submit_command

POLL_INTERVAL_SECONDS = max(
    0.5, float(os.getenv("KOALABYTE_T114_MENU_STATUS_INTERVAL", "3.0"))
)
BROKER_WAIT_SECONDS = max(
    0.15, float(os.getenv("KOALABYTE_T114_MENU_STATUS_BROKER_SECONDS", "0.9"))
)
STATUS_MAX_AGE_SECONDS = max(
    3.0, float(os.getenv("KOALABYTE_T114_STATUS_MAX_AGE", "15.0"))
)
STATUS_SNAPSHOT_PATH = Path(
    os.getenv(
        "KOALABYTE_T114_STATUS_SNAPSHOT",
        "logs/ble_nodes/t114_status_snapshot.json",
    )
)
STATUS_REQUESTS = (
    {"type": "node_roles"},
    {"type": "ble_status"},
    {"type": "ble_tx_status"},
    {"type": "gnss_status"},
    {"type": "status"},
)


@dataclass
class T114MenuSnapshot:
    checked_at: float = 0.0
    source: str = "none"
    port: str = ""
    online: bool = False
    responding: bool = False
    ble_ready: bool = False
    ble_scan_active: bool = False
    gnss_enabled: bool = False
    gnss_has_fix: bool = False
    tx_status: str = "off"
    tx_reason: str = ""
    tx_active: bool = False
    error: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)


_LAST_SNAPSHOT = T114MenuSnapshot()
_LAST_PHRASES: dict[str, tuple[str, str]] = {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _stable_port_candidates() -> list[str]:
    candidates = [
        os.getenv("KOALABYTE_HELTEC_USB_PORT", ""),
        os.getenv("KOALABYTE_PRIMARY_BLE_PORT", ""),
        os.getenv("KOALABYTE_PRIMARY_GNSS_PORT", ""),
        os.getenv("HELTEC_PORT", ""),
        "/dev/koalabyte-heltec",
        "/dev/koalabyte-heltec-t114",
    ]
    return list(dict.fromkeys(value for value in candidates if value))


def _visible_port() -> str:
    for port in _stable_port_candidates():
        try:
            if Path(port).exists():
                return port
        except OSError:
            continue
    return ""


def _socket_ready(path: Path) -> bool:
    try:
        return stat.S_ISSOCK(path.stat().st_mode)
    except OSError:
        return False


def _request_brokered_status() -> bool:
    """Ask the exclusive Heltec owner for fresh status without opening the tty."""

    bus_socket = socket_path("heltec")
    if not _socket_ready(bus_socket):
        return False
    previous_mtime = (
        STATUS_SNAPSHOT_PATH.stat().st_mtime_ns
        if STATUS_SNAPSHOT_PATH.exists()
        else 0
    )
    delivered = False
    for payload in STATUS_REQUESTS:
        submission = submit_command(
            "heltec",
            payload,
            queue_if_unavailable=False,
        )
        delivered = delivered or submission.delivered
    if not delivered:
        return False

    deadline = time.monotonic() + BROKER_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            if (
                STATUS_SNAPSHOT_PATH.exists()
                and STATUS_SNAPSHOT_PATH.stat().st_mtime_ns > previous_mtime
            ):
                return True
        except OSError:
            pass
        time.sleep(0.05)
    return STATUS_SNAPSHOT_PATH.exists()


def _snapshot_from_owner(payload: dict[str, Any], *, refreshed: bool) -> T114MenuSnapshot:
    updated_at = float(payload.get("updated_at") or 0.0)
    age = max(0.0, time.time() - updated_at) if updated_at else float("inf")
    fresh = age <= STATUS_MAX_AGE_SECONDS
    port = str(payload.get("port") or _visible_port())
    online = bool(payload.get("online", False)) and fresh
    responding = bool(payload.get("responding", False)) and fresh
    error = str(payload.get("error") or "")
    if not fresh:
        error = (
            f"Heltec owner snapshot is stale ({age:.1f}s); waiting for a fresh response"
        )
    elif not refreshed and not responding and not error:
        error = "Heltec owner is running but no fresh status response is available"

    tx_status = str(payload.get("tx_status") or "off").lower()
    if tx_status not in {"on", "off", "blocked"}:
        tx_status = "on" if bool(payload.get("tx_active", False)) else "off"
    if not online:
        tx_status = "blocked"

    return T114MenuSnapshot(
        checked_at=time.monotonic(),
        source="serial_owner_snapshot" if refreshed else "cached_owner_snapshot",
        port=port,
        online=online,
        responding=responding,
        ble_ready=bool(payload.get("ble_ready", False)) and fresh,
        ble_scan_active=bool(payload.get("ble_scan_active", False)) and fresh,
        gnss_enabled=bool(payload.get("gnss_enabled", False)) and fresh,
        gnss_has_fix=bool(payload.get("gnss_has_fix", False)) and fresh,
        tx_status=tx_status,
        tx_reason=str(payload.get("tx_reason") or "")[:160],
        tx_active=bool(payload.get("tx_active", False)) and fresh,
        error=error,
        events=[
            {
                "type": str(payload.get("last_event_type") or ""),
                "updated_at": updated_at,
                "snapshot_age_seconds": age,
                "coordinates_persisted_here": bool(
                    payload.get("coordinates_persisted_here", False)
                ),
            }
        ],
    )


def _poll_snapshot() -> T114MenuSnapshot:
    refreshed = _request_brokered_status()
    payload = _read_json(STATUS_SNAPSHOT_PATH)
    if payload:
        snapshot = _snapshot_from_owner(payload, refreshed=refreshed)
        fix = _read_json(Path("logs/gnss/current_fix.json"))
        if fix.get("latitude") is not None and fix.get("longitude") is not None:
            snapshot.gnss_enabled = True
            snapshot.gnss_has_fix = True
        return snapshot

    visible = _visible_port()
    if visible:
        return T114MenuSnapshot(
            checked_at=time.monotonic(),
            source="stable_port_without_owner_snapshot",
            port=visible,
            online=True,
            responding=False,
            tx_status="blocked",
            error="Heltec stable port exists, but the serial owner has not published status",
        )
    return T114MenuSnapshot(
        checked_at=time.monotonic(),
        source="no_owner_or_stable_port",
        online=False,
        responding=False,
        tx_status="blocked",
        error="No Heltec serial-owner socket or stable T114 port is available",
    )


def _snapshot() -> T114MenuSnapshot:
    global _LAST_SNAPSHOT
    now = time.monotonic()
    if now - _LAST_SNAPSHOT.checked_at >= POLL_INTERVAL_SECONDS:
        _LAST_SNAPSHOT = _poll_snapshot()
    return _LAST_SNAPSHOT


def _phrase_for(command: str, snapshot: T114MenuSnapshot) -> tuple[str, str]:
    if command == "status:t114_link":
        if snapshot.responding:
            return (
                "Heltec Link: Connected",
                f"Brokered status: T114 owner responded on {snapshot.port}.",
            )
        if snapshot.online:
            return (
                "Heltec Link: Waiting",
                f"Stable port is visible at {snapshot.port}, but the owner has no fresh reply.",
            )
        return (
            "Heltec Link: Disconnected",
            "No Heltec owner or stable T114 port is available.",
        )

    if command == "status:t114_radio_gps":
        if not snapshot.online:
            return (
                "Radio/GPS: Offline",
                "T114 is disconnected, so BLE/GNSS status is unavailable.",
            )
        if not snapshot.responding:
            return (
                "Radio/GPS: Waiting",
                "T114 is visible, but the exclusive owner has no fresh BLE/GNSS response.",
            )
        ble_text = (
            "BLE scanning"
            if snapshot.ble_scan_active
            else ("BLE ready" if snapshot.ble_ready else "BLE offline")
        )
        if snapshot.gnss_has_fix:
            gps_text = "GPS fix"
        elif snapshot.gnss_enabled:
            gps_text = "GPS waiting"
        else:
            gps_text = "GPS no fix"
        return (
            f"Radio/GPS: {ble_text} · {gps_text}",
            f"Brokered through {snapshot.source}; the menu never opens the T114 tty.",
        )

    if command == "status:t114_tx":
        if not snapshot.online:
            return (
                "Lab Beacon TX: Blocked",
                "T114 is disconnected, so safe lab beacon TX is blocked.",
            )
        if not snapshot.responding:
            return (
                "Lab Beacon TX: Blocked",
                "T114 has no fresh owner response, so safe lab beacon TX stays blocked.",
            )
        if snapshot.tx_status == "blocked":
            return (
                "Lab Beacon TX: Blocked",
                snapshot.tx_reason
                or "Safe lab beacon TX is blocked by the T114 status check.",
            )
        if snapshot.tx_status == "on":
            return (
                "Lab Beacon TX: On",
                "Safe non-connectable owned-lab beacon is active.",
            )
        return (
            "Lab Beacon TX: Off",
            "Safe non-connectable owned-lab beacon is off.",
        )

    return "T114 Status: Unknown", "Unknown T114 status row."


def status_label_description(command: str) -> tuple[str, str]:
    """Return current T114 status without competing for its serial device."""

    phrase = _phrase_for(command, _snapshot())
    previous = _LAST_PHRASES.get(command)
    if previous == phrase:
        return previous
    _LAST_PHRASES[command] = phrase
    return phrase
