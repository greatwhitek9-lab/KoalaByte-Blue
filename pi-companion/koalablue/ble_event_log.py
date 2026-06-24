from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PRIMARY_SOURCE = "heltec-t114-nrf52840"
LEGACY_PRIMARY_SOURCES = {"nrf52840-dongle"}


def clean_addr(value: Any) -> str:
    return str(value or "").strip().upper()


def is_primary_source(source: str) -> bool:
    source_l = source.lower()
    return source == PRIMARY_SOURCE or source in LEGACY_PRIMARY_SOURCES or "heltec" in source_l or "t114" in source_l


def normalize_ble_event(payload: dict[str, Any], *, default_source: str = "unknown") -> dict[str, Any]:
    source = str(payload.get("source") or payload.get("device") or default_source)
    role = str(payload.get("role") or ("primary" if is_primary_source(source) else "secondary"))
    now = time.time()
    return {
        "type": "ble_adv_seen",
        "source": source,
        "role": role,
        "addr": clean_addr(payload.get("addr") or payload.get("address")),
        "addr_type": str(payload.get("addr_type") or payload.get("address_type") or ""),
        "rssi": payload.get("rssi"),
        "name": str(payload.get("name") or payload.get("local_name") or ""),
        "manufacturer": str(payload.get("manufacturer") or payload.get("manufacturer_data") or ""),
        "service_uuids": payload.get("service_uuids") or [],
        "transport": str(payload.get("transport") or ""),
        "active_scan": bool(payload.get("active_scan", False)),
        "seen_ms": payload.get("seen_ms"),
        "first_seen_ts": float(payload.get("ts") or now),
        "last_seen_ts": now,
        "raw": payload,
    }


def event_identity(event: dict[str, Any]) -> str:
    addr = clean_addr(event.get("addr"))
    if addr:
        return addr
    name = str(event.get("name") or "").strip().lower()
    source = str(event.get("source") or "unknown")
    return f"{source}:{name or 'unnamed'}"


def source_priority(source: str) -> int:
    source_l = source.lower()
    if is_primary_source(source):
        return 0
    if "esp32" in source_l or "dualeye" in source_l:
        return 1
    if "bluez" in source_l or "raspberry-pi" in source_l:
        return 2
    return 3


@dataclass
class BleEventDeduper:
    ttl_seconds: float = 5.0
    rssi_change_db: int = 8
    latest: dict[str, dict[str, Any]] = field(default_factory=dict)

    def should_emit(self, event: dict[str, Any]) -> bool:
        key = event_identity(event)
        now = float(event.get("last_seen_ts") or time.time())
        previous = self.latest.get(key)
        if previous is None:
            self.latest[key] = event
            return True

        previous_source = str(previous.get("source") or "")
        new_source = str(event.get("source") or "")
        if source_priority(new_source) < source_priority(previous_source):
            self.latest[key] = event
            return True

        elapsed = now - float(previous.get("last_seen_ts") or 0)
        try:
            moved = abs(int(event.get("rssi")) - int(previous.get("rssi"))) >= self.rssi_change_db
        except Exception:
            moved = False

        if elapsed >= self.ttl_seconds or moved:
            if source_priority(new_source) <= source_priority(previous_source):
                self.latest[key] = event
            else:
                merged = dict(previous)
                merged["last_seen_ts"] = now
                merged["secondary_sources"] = sorted(set(merged.get("secondary_sources", [])) | {new_source})
                self.latest[key] = merged
            return True
        return False


class BleEventLog:
    def __init__(self, log_dir: str | Path = "logs/ble_nodes") -> None:
        self.log_dir = Path(log_dir)
        self.event_path = self.log_dir / "ble_events.jsonl"
        self.state_path = self.log_dir / "ble_state.json"

    def append(self, event: dict[str, Any]) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with self.event_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
        self.state_path.write_text(json.dumps(event, indent=2, sort_keys=True), encoding="utf-8")