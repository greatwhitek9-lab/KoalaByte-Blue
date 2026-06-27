from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from .gnss_location import current_fix, valid_lat_lon

DEFAULT_CAPTURE_DIRS = [Path("/blecaptures"), Path("logs/eucalyptus"), Path("logs/koala_bluez"), Path("/blecaptures/koala_kapture")]
DEFAULT_OUTPUT_DIR = Path("logs/eucalyptus")
DEFAULT_STATUS_PATH = DEFAULT_OUTPUT_DIR / "eucalyptus_wigle_status.json"
DEFAULT_MAX_RECORDS = int(os.getenv("KOALABYTE_EUCALYPTUS_MAX_WIGLE_RECORDS", "5000"))
WIGLE_UPLOAD_URL = os.getenv("WIGLE_UPLOAD_URL", "https://api.wigle.net/api/v2/file/upload")

GPS_ENABLE_ENV = "KOALABYTE_EUCALYPTUS_GPS_LOGGING"
WIGLE_UPLOAD_ENABLE_ENV = "KOALABYTE_EUCALYPTUS_WIGLE_UPLOAD"
WIGLE_API_NAME_ENV = os.getenv("KOALABYTE_WIGLE_API_NAME_ENV", "WIGLE_API_NAME")
WIGLE_API_TOKEN_ENV = os.getenv("KOALABYTE_WIGLE_API_TOKEN_ENV", "WIGLE_API_TOKEN")

ADDRESS_KEYS = ("address", "addr", "mac", "mac_address", "device_address", "bssid", "bdaddr")
NAME_KEYS = ("name", "local_name", "ssid", "device_name", "label")
RSSI_KEYS = ("rssi", "signal", "level", "dbm")
LAT_KEYS = ("latitude", "lat", "currentlatitude", "CurrentLatitude")
LON_KEYS = ("longitude", "lon", "lng", "currentlongitude", "CurrentLongitude")
ALT_KEYS = ("altitude_meters", "alt", "altitude", "AltitudeMeters")
ACC_KEYS = ("accuracy_meters", "accuracy", "AccuracyMeters")
TIME_KEYS = ("timestamp", "first_seen", "seen_at", "captured_at", "captured_at_utc")


@dataclass(frozen=True)
class EucalyptusTrailResult:
    status: str
    records_read: int
    records_written: int
    records_with_location: int
    output_jsonl_path: str
    wigle_csv_path: str
    status_path: str
    gps_source: str
    notes: list[str] = field(default_factory=list)


def _truthy(value: object) -> bool:
    return str(value).strip() in {"1", "true", "TRUE", "yes", "YES", "on", "ON", "enabled", "ENABLED"}


def _safe_float(value: object) -> Optional[float]:
    if value in {None, ""}:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> Optional[int]:
    if value in {None, ""}:
        return None
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _first(record: dict[str, Any], keys: Iterable[str]) -> object:
    lowered = {str(key).lower(): value for key, value in record.items()}
    for key in keys:
        if key in record and record[key] not in {None, ""}:
            return record[key]
        value = lowered.get(str(key).lower())
        if value not in {None, ""}:
            return value
    return None


def _utc_timestamp(value: object) -> str:
    if value in {None, ""}:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    text = str(value).strip()
    try:
        return datetime.fromtimestamp(float(text), timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except ValueError:
        return text


def _iter_capture_files(capture_dirs: Iterable[Path]) -> Iterable[Path]:
    allowed = {".jsonl", ".json", ".csv", ".ndjson", ".log", ".txt"}
    for directory in capture_dirs:
        try:
            if not directory.exists() or not directory.is_dir():
                continue
            for path in sorted(directory.rglob("*")):
                if path.is_file() and path.suffix.lower() in allowed:
                    yield path
        except PermissionError:
            continue


def _iter_records_from_file(path: Path) -> Iterable[dict[str, Any]]:
    suffix = path.suffix.lower()
    try:
        if suffix in {".jsonl", ".ndjson", ".log", ".txt"}:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    yield payload
                elif isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, dict):
                            yield item
        elif suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict):
                        yield item
            elif isinstance(payload, dict):
                for key in ("observations", "devices", "records", "results", "events"):
                    value = payload.get(key)
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                yield item
                        return
                yield payload
        elif suffix == ".csv":
            with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                for row in csv.DictReader(handle):
                    yield dict(row)
    except Exception:
        return


def _fixed_env_fix() -> Optional[dict[str, object]]:
    lat = _safe_float(os.getenv("KOALABYTE_EUCALYPTUS_FIXED_LAT") or os.getenv("KOALABYTE_GNSS_LAT"))
    lon = _safe_float(os.getenv("KOALABYTE_EUCALYPTUS_FIXED_LON") or os.getenv("KOALABYTE_GNSS_LON"))
    if not valid_lat_lon(lat, lon):
        return None
    return {
        "latitude": lat,
        "longitude": lon,
        "altitude_meters": _safe_float(os.getenv("KOALABYTE_EUCALYPTUS_FIXED_ALT") or os.getenv("KOALABYTE_GNSS_ALT")),
        "accuracy_meters": _safe_float(os.getenv("KOALABYTE_EUCALYPTUS_FIXED_ACCURACY") or os.getenv("KOALABYTE_GNSS_ACCURACY")) or 25.0,
        "source": "eucalyptus_fixed_env",
        "status": "fix",
    }


def eucalyptus_location_fix() -> Optional[dict[str, object]]:
    fixed = _fixed_env_fix()
    if fixed:
        return fixed
    if not _truthy(os.getenv(GPS_ENABLE_ENV)):
        return None
    fix = current_fix(authorized=True, prompt=False)
    return asdict(fix) if fix is not None else None


def _record_location(record: dict[str, Any], default_fix: Optional[dict[str, object]]) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float], str]:
    lat = _safe_float(_first(record, LAT_KEYS))
    lon = _safe_float(_first(record, LON_KEYS))
    alt = _safe_float(_first(record, ALT_KEYS))
    acc = _safe_float(_first(record, ACC_KEYS))
    if valid_lat_lon(lat, lon):
        return lat, lon, alt, acc, "record"
    if default_fix:
        fix_lat = _safe_float(default_fix.get("latitude"))
        fix_lon = _safe_float(default_fix.get("longitude"))
        if valid_lat_lon(fix_lat, fix_lon):
            return fix_lat, fix_lon, _safe_float(default_fix.get("altitude_meters")), _safe_float(default_fix.get("accuracy_meters")), str(default_fix.get("source", "current_fix"))
    return None, None, None, None, "none"


def _normalise_record(record: dict[str, Any], source_path: Path, default_fix: Optional[dict[str, object]]) -> Optional[dict[str, object]]:
    address = str(_first(record, ADDRESS_KEYS) or "").strip()
    if not address:
        return None
    name = str(_first(record, NAME_KEYS) or "").strip()
    rssi = _safe_int(_first(record, RSSI_KEYS))
    lat, lon, alt, acc, location_source = _record_location(record, default_fix)
    out: dict[str, object] = {
        "type": "eucalyptus_ble_observation",
        "address": address,
        "name": name,
        "rssi": rssi,
        "first_seen": _utc_timestamp(_first(record, TIME_KEYS)),
        "source_path": str(source_path),
        "latitude": lat,
        "longitude": lon,
        "altitude_meters": alt,
        "accuracy_meters": acc,
        "location_source": location_source,
        "safety_scope": "passive BLE observation with optional operator-authorized GNSS enrichment; no pairing, probing, connection, or disruption",
    }
    return out


def _wigle_row(record: dict[str, object]) -> Optional[dict[str, object]]:
    lat = _safe_float(record.get("latitude"))
    lon = _safe_float(record.get("longitude"))
    if not valid_lat_lon(lat, lon):
        return None
    return {
        "MAC": record.get("address", ""),
        "SSID": record.get("name", ""),
        "AuthMode": "[BLE]",
        "FirstSeen": record.get("first_seen", ""),
        "Channel": "",
        "RSSI": record.get("rssi", ""),
        "CurrentLatitude": lat,
        "CurrentLongitude": lon,
        "AltitudeMeters": record.get("altitude_meters") or "",
        "AccuracyMeters": record.get("accuracy_meters") or "",
        "Type": "BLE",
    }


def _write_status(payload: dict[str, object], path: Path = DEFAULT_STATUS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_gps_trail(*, capture_dirs: Iterable[Path] = DEFAULT_CAPTURE_DIRS, output_dir: Path = DEFAULT_OUTPUT_DIR, max_records: int = DEFAULT_MAX_RECORDS) -> EucalyptusTrailResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    jsonl_path = output_dir / f"eucalyptus_gps_trail_{stamp}.jsonl"
    wigle_csv_path = output_dir / f"eucalyptus_wigle_ble_{stamp}.csv"
    fix = eucalyptus_location_fix()
    records_read = 0
    records_written = 0
    records_with_location = 0
    notes: list[str] = []
    if fix is None:
        notes.append(f"GPS enrichment is disabled or locked. Set {GPS_ENABLE_ENV}=1 and unlock the protected location gate, or set KOALABYTE_EUCALYPTUS_FIXED_LAT/LON for a lab test.")

    with jsonl_path.open("w", encoding="utf-8") as jsonl, wigle_csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        csv_file.write("WigleWifi-1.4,appRelease=KoalaByteBlue,model=KoalaByteBlue,release=Main,device=KoalaByteBlue,display=Eucalyptus,board=RaspberryPi3B\n")
        writer = csv.DictWriter(csv_file, fieldnames=["MAC", "SSID", "AuthMode", "FirstSeen", "Channel", "RSSI", "CurrentLatitude", "CurrentLongitude", "AltitudeMeters", "AccuracyMeters", "Type"])
        writer.writeheader()
        for path in _iter_capture_files(capture_dirs):
            for raw in _iter_records_from_file(path):
                records_read += 1
                normalised = _normalise_record(raw, path, fix)
                if normalised is None:
                    continue
                jsonl.write(json.dumps(normalised, sort_keys=True) + "\n")
                records_written += 1
                row = _wigle_row(normalised)
                if row is not None:
                    writer.writerow(row)
                    records_with_location += 1
                if records_written >= max_records:
                    break
            if records_written >= max_records:
                break

    status = "EUCALYPTUS_GPS_TRAIL_READY" if records_written else "EUCALYPTUS_GPS_TRAIL_EMPTY"
    result = EucalyptusTrailResult(
        status=status,
        records_read=records_read,
        records_written=records_written,
        records_with_location=records_with_location,
        output_jsonl_path=str(jsonl_path),
        wigle_csv_path=str(wigle_csv_path),
        status_path=str(DEFAULT_STATUS_PATH),
        gps_source=str(fix.get("source", "none")) if fix else "none",
        notes=notes,
    )
    _write_status(asdict(result) | {"updated_at": time.time(), "wigle_upload_enabled": _truthy(os.getenv(WIGLE_UPLOAD_ENABLE_ENV)), "wigle_credentials_configured": bool(os.getenv(WIGLE_API_NAME_ENV) and os.getenv(WIGLE_API_TOKEN_ENV))})
    return result


def upload_status() -> dict[str, object]:
    capture_files = list(_iter_capture_files(DEFAULT_CAPTURE_DIRS))
    fix = eucalyptus_location_fix()
    payload = {
        "status": "EUCALYPTUS_WIGLE_UPLOAD_READY" if _truthy(os.getenv(WIGLE_UPLOAD_ENABLE_ENV)) and os.getenv(WIGLE_API_NAME_ENV) and os.getenv(WIGLE_API_TOKEN_ENV) else "EUCALYPTUS_WIGLE_UPLOAD_NOT_ARMED",
        "capture_dirs": [str(path) for path in DEFAULT_CAPTURE_DIRS],
        "capture_files_seen": len(capture_files),
        "gps_logging_enabled_env": GPS_ENABLE_ENV,
        "gps_logging_enabled": _truthy(os.getenv(GPS_ENABLE_ENV)) or _fixed_env_fix() is not None,
        "gps_fix_available": fix is not None,
        "gps_source": str(fix.get("source", "none")) if fix else "none",
        "wigle_upload_enabled_env": WIGLE_UPLOAD_ENABLE_ENV,
        "wigle_upload_enabled": _truthy(os.getenv(WIGLE_UPLOAD_ENABLE_ENV)),
        "wigle_api_name_env": WIGLE_API_NAME_ENV,
        "wigle_api_token_env": WIGLE_API_TOKEN_ENV,
        "wigle_credentials_configured": bool(os.getenv(WIGLE_API_NAME_ENV) and os.getenv(WIGLE_API_TOKEN_ENV)),
        "safety_scope": "Passive BLE observations only. WiGLE upload requires explicit env enablement and credentials.",
        "updated_at": time.time(),
    }
    _write_status(payload)
    return payload


def upload_to_wigle(*, dry_run: bool = False) -> dict[str, object]:
    trail = build_gps_trail()
    payload = asdict(trail)
    payload.update({"upload_url": WIGLE_UPLOAD_URL, "dry_run": dry_run})
    if trail.records_with_location <= 0:
        payload.update({"status": "EUCALYPTUS_WIGLE_UPLOAD_BLOCKED", "reason": "No records with latitude/longitude were available."})
        _write_status(payload)
        return payload
    if dry_run:
        payload.update({"status": "EUCALYPTUS_WIGLE_UPLOAD_DRY_RUN", "reason": "CSV built but network upload was not attempted."})
        _write_status(payload)
        return payload
    if not _truthy(os.getenv(WIGLE_UPLOAD_ENABLE_ENV)):
        payload.update({"status": "EUCALYPTUS_WIGLE_UPLOAD_BLOCKED", "reason": f"Set {WIGLE_UPLOAD_ENABLE_ENV}=1 to arm WiGLE upload."})
        _write_status(payload)
        return payload
    api_name = os.getenv(WIGLE_API_NAME_ENV)
    api_token = os.getenv(WIGLE_API_TOKEN_ENV)
    if not api_name or not api_token:
        payload.update({"status": "EUCALYPTUS_WIGLE_UPLOAD_BLOCKED", "reason": f"Missing {WIGLE_API_NAME_ENV}/{WIGLE_API_TOKEN_ENV}."})
        _write_status(payload)
        return payload
    try:
        import requests  # type: ignore
        with Path(trail.wigle_csv_path).open("rb") as handle:
            response = requests.post(WIGLE_UPLOAD_URL, auth=(api_name, api_token), files={"file": (Path(trail.wigle_csv_path).name, handle, "text/csv")}, data={"donate": "on"}, timeout=60)
        payload.update({"status": "EUCALYPTUS_WIGLE_UPLOAD_COMPLETE" if response.ok else "EUCALYPTUS_WIGLE_UPLOAD_FAILED", "http_status": response.status_code, "response_text": response.text[:1000]})
    except Exception as exc:
        payload.update({"status": "EUCALYPTUS_WIGLE_UPLOAD_FAILED", "error": str(exc)})
    _write_status(payload)
    return payload


def control_status(action: str) -> dict[str, object]:
    if action == "status":
        return upload_status()
    if action in {"start", "stop", "restart"}:
        payload = {
            "status": f"EUCALYPTUS_CANOPY_{action.upper()}_RECORDED",
            "action": action,
            "note": "Menu action recorded. Passive BLE service control remains a local service/boot configuration concern; GPS trail and WiGLE readiness are handled by this helper.",
            "updated_at": time.time(),
        }
        _write_status(payload)
        return payload
    if action in {"upload-status", "wigle-status"}:
        return upload_status()
    if action in {"gps-trail", "trail"}:
        return asdict(build_gps_trail())
    if action in {"wigle-upload", "upload"}:
        return upload_to_wigle()
    return {"status": "EUCALYPTUS_UNKNOWN_ACTION", "action": action}
