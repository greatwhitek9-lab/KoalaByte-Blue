from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .location_password_gate import ensure_unlocked

DEFAULT_FIX_PATH = Path("logs/gnss/current_fix.json")
DEFAULT_GNSS_LOG = Path("logs/gnss/gnss_events.jsonl")
AUTHORIZED_LOCATION_ENV = "KOALABYTE_AUTHORIZED_LOCATION_LOGGING"
PRIMARY_GNSS_PORT_ENV = "KOALABYTE_HELTEC_USB_PORT"

_LAT_PATTERN = re.compile(r"\b(?:lat|latitude)\s*[:=]\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)
_LON_PATTERN = re.compile(r"\b(?:lon|lng|long|longitude)\s*[:=]\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)
_ALT_PATTERN = re.compile(r"\b(?:alt|altitude)\s*[:=]\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)


@dataclass(frozen=True)
class GnssFix:
    latitude: Optional[float]
    longitude: Optional[float]
    altitude_meters: Optional[float] = None
    accuracy_meters: Optional[float] = None
    source: str = "unknown"
    status: str = "no_fix"
    captured_at_utc: str = ""
    safety_scope: str = "authorized password-protected location logging only"
    note: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def location_logging_authorized(enabled: Optional[bool] = None, *, password: Optional[str] = None, prompt: bool = False) -> bool:
    if enabled is False:
        return False
    if not ensure_unlocked(password=password, prompt=prompt):
        return False
    return True


def locked_location_dict(reason: str = "password_required") -> dict[str, object]:
    return {
        "latitude": None,
        "longitude": None,
        "altitude_meters": None,
        "accuracy_meters": None,
        "source": "location_password_gate",
        "status": reason,
        "captured_at_utc": utc_now(),
        "safety_scope": "authorized password-protected location logging only",
        "note": "location fields are present by default, but coordinates are not shown to protected actions until the operator unlocks the protected-actions password gate",
    }


def valid_lat_lon(latitude: Optional[float], longitude: Optional[float]) -> bool:
    return latitude is not None and longitude is not None and -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0


def _float_env(name: str) -> Optional[float]:
    value = os.environ.get(name)
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fix_to_dict(fix: Optional[GnssFix]) -> dict[str, object]:
    if fix is None:
        return locked_location_dict("password_required")
    return asdict(fix)


def parse_meshtastic_info_text(text: str) -> Optional[GnssFix]:
    lat = _LAT_PATTERN.search(text or "")
    lon = _LON_PATTERN.search(text or "")
    if not lat or not lon:
        return None
    try:
        latitude = float(lat.group(1))
        longitude = float(lon.group(1))
    except ValueError:
        return None
    if not valid_lat_lon(latitude, longitude):
        return None
    alt_match = _ALT_PATTERN.search(text or "")
    altitude = None
    if alt_match:
        try:
            altitude = float(alt_match.group(1))
        except ValueError:
            altitude = None
    return GnssFix(latitude, longitude, altitude, None, "meshtastic_info", "fix", utc_now(), note="parsed from meshtastic --info output")


def env_fix() -> Optional[GnssFix]:
    latitude = _float_env("KOALABYTE_GNSS_LAT")
    longitude = _float_env("KOALABYTE_GNSS_LON")
    altitude = _float_env("KOALABYTE_GNSS_ALT")
    accuracy = _float_env("KOALABYTE_GNSS_ACCURACY")
    if not valid_lat_lon(latitude, longitude):
        return None
    return GnssFix(latitude, longitude, altitude, accuracy, "environment", "fix", utc_now(), note="manual/test fix from environment")


def saved_fix(path: str | Path = DEFAULT_FIX_PATH) -> Optional[GnssFix]:
    file_path = Path(path)
    if not file_path.exists():
        return None
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        latitude = float(data["latitude"]) if data.get("latitude") is not None else None
        longitude = float(data["longitude"]) if data.get("longitude") is not None else None
        if not valid_lat_lon(latitude, longitude):
            return None
        return GnssFix(
            latitude=latitude,
            longitude=longitude,
            altitude_meters=data.get("altitude_meters"),
            accuracy_meters=data.get("accuracy_meters"),
            source=str(data.get("source", "saved_fix")),
            status=str(data.get("status", "fix")),
            captured_at_utc=str(data.get("captured_at_utc", utc_now())),
            note=str(data.get("note", "loaded saved GNSS fix")),
        )
    except Exception:
        return None


def fix_from_t114_event(event: dict[str, object]) -> Optional[GnssFix]:
    if str(event.get("type")) != "gnss_fix":
        return None
    try:
        latitude = float(event["latitude"]) if event.get("latitude") is not None else None
        longitude = float(event["longitude"]) if event.get("longitude") is not None else None
    except (TypeError, ValueError):
        return None
    if not valid_lat_lon(latitude, longitude):
        return None
    altitude = None
    try:
        altitude = float(event["altitude_meters"]) if event.get("altitude_meters") is not None else None
    except (TypeError, ValueError):
        altitude = None
    return GnssFix(
        latitude=latitude,
        longitude=longitude,
        altitude_meters=altitude,
        accuracy_meters=None,
        source="heltec-t114-gnss",
        status="fix",
        captured_at_utc=utc_now(),
        note="primary device GPS fix from Heltec T114 GNSS via nRF52840 USB CDC JSON",
    )


def write_primary_t114_fix_event(event: dict[str, object], path: str | Path = DEFAULT_FIX_PATH, log_path: str | Path = DEFAULT_GNSS_LOG) -> Optional[dict[str, object]]:
    fix = fix_from_t114_event(event)
    if fix is None:
        return None
    data = asdict(fix)
    data["main_device_gps"] = True
    data["works_alongside"] = ["ble", "lora", "wifi"]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    event_path = Path(log_path)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"event": "primary_t114_gnss_fix_saved", "timestamp": time.time(), "fix": data}, sort_keys=True) + "\n")
    return data


def write_gnss_status_event(event: dict[str, object], log_path: str | Path = DEFAULT_GNSS_LOG) -> None:
    event_path = Path(log_path)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"event": "primary_t114_gnss_status", "timestamp": time.time(), "status": event}, sort_keys=True) + "\n")


def t114_serial_fix(port: str, baud: int = 115200, timeout: float = 2.5) -> Optional[GnssFix]:
    try:
        import serial  # type: ignore
        with serial.Serial(port, baudrate=baud, timeout=0.15, write_timeout=0.35) as ser:
            ser.write(b'{"type":"gnss_current_fix"}\n')
            deadline = time.time() + timeout
            while time.time() < deadline:
                raw = ser.readline()
                if not raw:
                    continue
                try:
                    event = json.loads(raw.decode("utf-8", errors="replace").strip())
                except Exception:
                    continue
                if isinstance(event, dict) and event.get("type") == "gnss_fix":
                    return fix_from_t114_event(event)
    except Exception:
        return None
    return None


def meshtastic_info_fix(port: str = "/dev/ttyUSB0", timeout: float = 15.0) -> Optional[GnssFix]:
    try:
        result = subprocess.run(["meshtastic", "--port", port, "--info"], capture_output=True, text=True, timeout=timeout, check=False)
    except Exception:
        return None
    return parse_meshtastic_info_text("\n".join([result.stdout or "", result.stderr or ""]))


def current_fix(*, authorized: Optional[bool] = None, meshtastic_port: Optional[str] = None, heltec_port: Optional[str] = None, saved_path: str | Path = DEFAULT_FIX_PATH, password: Optional[str] = None, prompt: bool = False) -> Optional[GnssFix]:
    if not location_logging_authorized(enabled=authorized, password=password, prompt=prompt):
        return None
    primary_port = heltec_port or os.environ.get("KOALABYTE_PRIMARY_GNSS_PORT") or os.environ.get("KOALABYTE_HELTEC_USB_PORT") or os.environ.get("KOALABYTE_PRIMARY_BLE_PORT")
    return env_fix() or saved_fix(saved_path) or (t114_serial_fix(primary_port) if primary_port else None) or (meshtastic_info_fix(meshtastic_port) if meshtastic_port else None)


def write_current_fix(fix: GnssFix, path: str | Path = DEFAULT_FIX_PATH, log_path: str | Path = DEFAULT_GNSS_LOG) -> dict[str, object]:
    if not location_logging_authorized(enabled=True):
        raise PermissionError("location logging is locked; unlock with the protected-actions password before writing a GNSS fix")
    data = asdict(fix)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    event_path = Path(log_path)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"event": "gnss_fix_saved", "timestamp": time.time(), "fix": data}, sort_keys=True) + "\n")
    return data
