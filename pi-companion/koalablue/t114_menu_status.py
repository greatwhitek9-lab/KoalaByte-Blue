from __future__ import annotations

import glob
import json
import os
import time
from pathlib import Path
from typing import Any

STATUS_TTL_SECONDS = 4.0
_CACHE: dict[str, tuple[float, tuple[str, str]]] = {}


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


def _connected_port() -> str:
    for port in _candidate_ports():
        try:
            if Path(port).exists():
                return port
        except Exception:
            continue
    return ""


def _gnss_fix() -> dict[str, Any]:
    return _read_json(Path("logs/gnss/current_fix.json"))


def _latest_t114_status() -> dict[str, Any]:
    payload = _latest_json("logs/hardware_validation/t114_combined_status_*.json")
    if payload:
        return payload
    return _latest_json("logs/t114_bluez/t114_combined_status_*.json")


def _latest_tx_status_event() -> dict[str, Any]:
    for pattern in ("logs/hardware_validation/t114_combined_tx-status_*.json", "logs/t114_bluez/t114_combined_tx-status_*.json"):
        payload = _latest_json(pattern)
        for event in payload.get("t114_serial_events", []) if isinstance(payload, dict) else []:
            if isinstance(event, dict) and event.get("type") == "ble_tx_status":
                return event
        if payload:
            return payload
    status_payload = _latest_t114_status()
    for event in status_payload.get("t114_serial_events", []) if isinstance(status_payload, dict) else []:
        if isinstance(event, dict) and event.get("type") == "ble_tx_status":
            return event
    return {}


def _status_label(command: str) -> tuple[str, str]:
    port = _connected_port()
    connected = bool(port)

    if command == "status:t114_link":
        if connected:
            return "Heltec Link: Connected", f"Heltec T114 is visible to the Pi at {port}."
        return "Heltec Link: Disconnected", "Heltec T114 is not visible yet. Plug it in or check /dev/koalabyte-heltec."

    if command == "status:t114_radio_gps":
        status_payload = _latest_t114_status()
        events = status_payload.get("t114_serial_events", []) if isinstance(status_payload, dict) else []
        ble_ready = connected
        gnss_ready = False
        has_fix = False
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") == "ble_status":
                ble_ready = bool(event.get("ble_ready", ble_ready))
            if event.get("type") == "gnss_status":
                gnss_ready = bool(event.get("enabled", event.get("gnss_ready", gnss_ready)))
                has_fix = bool(event.get("has_fix", has_fix))
            if event.get("type") == "gnss_fix":
                has_fix = True
                gnss_ready = True
        fix = _gnss_fix()
        if fix:
            has_fix = bool(fix.get("latitude") is not None and fix.get("longitude") is not None)
            gnss_ready = gnss_ready or has_fix
        ble_text = "BLE ready" if ble_ready else "BLE offline"
        if has_fix:
            gps_text = "GPS fix"
        elif gnss_ready:
            gps_text = "GPS waiting"
        else:
            gps_text = "GPS no fix"
        return f"Radio/GPS: {ble_text} · {gps_text}", "Live summary of the Heltec T114 radio and GNSS state."

    if command == "status:t114_tx":
        event = _latest_tx_status_event()
        raw_status = str(event.get("status", "")).lower() if isinstance(event, dict) else ""
        adv_active = bool(event.get("adv_active", False)) if isinstance(event, dict) else False
        if not connected:
            return "Lab Beacon TX: Blocked", "T114 is disconnected, so the safe lab beacon cannot transmit."
        if raw_status == "blocked":
            return "Lab Beacon TX: Blocked", str(event.get("reason", "Safe lab beacon TX is currently blocked."))
        if adv_active or raw_status == "started":
            return "Lab Beacon TX: On", "Safe non-connectable owned-lab beacon is currently active."
        return "Lab Beacon TX: Off", "Safe non-connectable owned-lab beacon is currently off."

    return "T114 Status: Unknown", "Unknown T114 status row."


def status_label_description(command: str) -> tuple[str, str]:
    now = time.monotonic()
    cached = _CACHE.get(command)
    if cached and now - cached[0] <= STATUS_TTL_SECONDS:
        return cached[1]
    result = _status_label(command)
    _CACHE[command] = (now, result)
    return result
