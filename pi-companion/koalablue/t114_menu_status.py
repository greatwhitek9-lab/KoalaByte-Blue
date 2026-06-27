from __future__ import annotations

import glob
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_BAUD = 115200
POLL_INTERVAL_SECONDS = float(os.getenv("KOALABYTE_T114_MENU_STATUS_INTERVAL", "3.0"))
SERIAL_POLL_SECONDS = float(os.getenv("KOALABYTE_T114_MENU_STATUS_SERIAL_SECONDS", "0.75"))


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
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _latest_json(pattern: str) -> dict[str, Any]:
    candidates = [Path(p) for p in glob.glob(pattern)]
    if not candidates:
        return {}
    try:
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
    except Exception:
        return {}
    return _read_json(newest)


def _candidate_ports() -> list[str]:
    explicit = [
        os.getenv("KOALABYTE_HELTEC_USB_PORT", ""),
        os.getenv("KOALABYTE_PRIMARY_BLE_PORT", ""),
        os.getenv("KOALABYTE_PRIMARY_GNSS_PORT", ""),
        os.getenv("HELTEC_PORT", ""),
    ]
    ports = [p for p in explicit if p]
    for pattern in ("/dev/koalabyte-heltec", "/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
        ports.extend(sorted(glob.glob(pattern)))
    seen: set[str] = set()
    unique: list[str] = []
    for port in ports:
        if port and port not in seen:
            seen.add(port)
            unique.append(port)
    return unique


def _visible_port() -> str:
    for port in _candidate_ports():
        try:
            if Path(port).exists():
                return port
        except Exception:
            continue
    return ""


def _serial_exchange(port: str) -> list[dict[str, Any]]:
    import serial  # type: ignore

    payloads = [
        {"type": "node_roles"},
        {"type": "ble_status"},
        {"type": "ble_tx_status"},
        {"type": "gnss_status"},
        {"type": "status"},
    ]
    events: list[dict[str, Any]] = []
    deadline = time.time() + SERIAL_POLL_SECONDS
    with serial.Serial(port, baudrate=DEFAULT_BAUD, timeout=0.08, write_timeout=0.25) as ser:
        for payload in payloads:
            ser.write((json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"))
        while time.time() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            try:
                event = json.loads(raw.decode("utf-8", errors="replace").strip())
            except Exception:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def _events_to_snapshot(events: list[dict[str, Any]], port: str, source: str) -> T114MenuSnapshot:
    snapshot = T114MenuSnapshot(
        checked_at=time.monotonic(),
        source=source,
        port=port,
        online=bool(port),
        responding=bool(events),
        ble_ready=bool(port),
        events=events,
    )
    for event in events:
        event_type = str(event.get("type", ""))
        if event_type == "node_roles":
            snapshot.online = True
            snapshot.responding = True
            snapshot.ble_ready = True
        elif event_type == "ble_status":
            snapshot.online = True
            snapshot.responding = True
            snapshot.ble_ready = bool(event.get("ble_ready", snapshot.ble_ready))
            snapshot.ble_scan_active = bool(event.get("scan_active", event.get("ble_scan_active", snapshot.ble_scan_active)))
        elif event_type == "ble_tx_status":
            snapshot.online = True
            snapshot.responding = True
            raw = str(event.get("status", "")).lower()
            snapshot.tx_active = bool(event.get("adv_active", False)) or raw == "started"
            snapshot.tx_reason = str(event.get("reason", ""))
            if raw == "blocked":
                snapshot.tx_status = "blocked"
            elif snapshot.tx_active:
                snapshot.tx_status = "on"
            else:
                snapshot.tx_status = "off"
        elif event_type == "gnss_status":
            snapshot.online = True
            snapshot.responding = True
            snapshot.gnss_enabled = bool(event.get("enabled", event.get("gnss_ready", snapshot.gnss_enabled)))
            snapshot.gnss_has_fix = bool(event.get("has_fix", snapshot.gnss_has_fix))
        elif event_type == "gnss_fix":
            snapshot.online = True
            snapshot.responding = True
            snapshot.gnss_enabled = True
            snapshot.gnss_has_fix = True
        elif event_type in {"heltec_mouth_status", "killerkoala_tft_ack"}:
            snapshot.online = True
            snapshot.responding = True
            snapshot.gnss_enabled = bool(event.get("gnss_enabled", snapshot.gnss_enabled))
            snapshot.ble_scan_active = bool(event.get("ble_scan_active", snapshot.ble_scan_active))
            snapshot.tx_active = bool(event.get("ble_tx_active", snapshot.tx_active))
            if snapshot.tx_active:
                snapshot.tx_status = "on"
    fix = _read_json(Path("logs/gnss/current_fix.json"))
    if fix.get("latitude") is not None and fix.get("longitude") is not None:
        snapshot.gnss_enabled = True
        snapshot.gnss_has_fix = True
    if not snapshot.online:
        snapshot.tx_status = "blocked"
    return snapshot


def _latest_log_events() -> tuple[str, list[dict[str, Any]]]:
    for pattern in (
        "logs/hardware_validation/t114_combined_status_*.json",
        "logs/t114_bluez/t114_combined_status_*.json",
        "logs/hardware_validation/t114_combined_tx-status_*.json",
        "logs/t114_bluez/t114_combined_tx-status_*.json",
    ):
        payload = _latest_json(pattern)
        events = payload.get("t114_serial_events", []) if isinstance(payload, dict) else []
        if isinstance(events, list) and events:
            port = str(payload.get("selected_port", "")) if isinstance(payload, dict) else ""
            return port, [event for event in events if isinstance(event, dict)]
    return "", []


def _poll_snapshot() -> T114MenuSnapshot:
    visible_port = _visible_port()
    for port in _candidate_ports():
        try:
            if not Path(port).exists():
                continue
            events = _serial_exchange(port)
            if events:
                return _events_to_snapshot(events, port, "live_serial")
        except Exception as exc:
            visible_port = visible_port or port
            last_error = str(exc)
            continue
    log_port, log_events = _latest_log_events()
    if log_events:
        snapshot = _events_to_snapshot(log_events, visible_port or log_port, "recent_log_fallback")
        snapshot.error = "live serial status unavailable; using most recent T114 log"
        return snapshot
    if visible_port:
        return T114MenuSnapshot(
            checked_at=time.monotonic(),
            source="port_visible_no_response",
            port=visible_port,
            online=True,
            responding=False,
            tx_status="blocked",
            error=last_error if "last_error" in locals() else "T114 port visible but no status response yet",
        )
    return T114MenuSnapshot(
        checked_at=time.monotonic(),
        source="no_port",
        online=False,
        responding=False,
        tx_status="blocked",
        error="No Heltec T114 serial port found",
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
            return "Heltec Link: Connected", f"Actively checked: T114 responded on {snapshot.port}."
        if snapshot.online:
            return "Heltec Link: Waiting", f"Port is visible at {snapshot.port}, but the T114 has not answered the live status poll yet."
        return "Heltec Link: Disconnected", "Actively checked: no Heltec T114 serial controller was found."

    if command == "status:t114_radio_gps":
        if not snapshot.online:
            return "Radio/GPS: Offline", "T114 is disconnected, so BLE/GNSS status is unavailable."
        if snapshot.online and not snapshot.responding:
            return "Radio/GPS: Waiting", "T114 port is visible, but live BLE/GNSS status has not answered yet."
        ble_text = "BLE scanning" if snapshot.ble_scan_active else ("BLE ready" if snapshot.ble_ready else "BLE offline")
        if snapshot.gnss_has_fix:
            gps_text = "GPS fix"
        elif snapshot.gnss_enabled:
            gps_text = "GPS waiting"
        else:
            gps_text = "GPS no fix"
        return f"Radio/GPS: {ble_text} · {gps_text}", f"Actively checked from {snapshot.source}."

    if command == "status:t114_tx":
        if not snapshot.online:
            return "Lab Beacon TX: Blocked", "T114 is disconnected, so safe lab beacon TX is blocked."
        if snapshot.online and not snapshot.responding:
            return "Lab Beacon TX: Blocked", "T114 is visible but not responding, so safe lab beacon TX stays blocked."
        if snapshot.tx_status == "blocked":
            reason = snapshot.tx_reason or "Safe lab beacon TX is blocked by the T114 status check."
            return "Lab Beacon TX: Blocked", reason
        if snapshot.tx_status == "on":
            return "Lab Beacon TX: On", "Safe non-connectable owned-lab beacon is active."
        return "Lab Beacon TX: Off", "Safe non-connectable owned-lab beacon is off."

    return "T114 Status: Unknown", "Unknown T114 status row."


def status_label_description(command: str) -> tuple[str, str]:
    """Return the current user-facing phrase for a status row.

    The status phrase is derived from an active T114 serial poll when possible.
    A phrase is replaced only when the underlying status category changes;
    repeated menu redraws keep the previous phrase stable.
    """

    phrase = _phrase_for(command, _snapshot())
    previous = _LAST_PHRASES.get(command)
    if previous == phrase:
        return previous
    _LAST_PHRASES[command] = phrase
    return phrase
