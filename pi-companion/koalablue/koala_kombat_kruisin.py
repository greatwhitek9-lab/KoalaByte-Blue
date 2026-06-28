from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from .gnss_location import current_fix, valid_lat_lon

ACTION_NAME = "Koala Kombat Kruisin'"
DISPLAY_NAME = "Koala Kombat Kruisin’"
DEFAULT_OUTPUT_DIR = Path("logs/koala_kombat_kruisin")
DEFAULT_STATUS_PATH = DEFAULT_OUTPUT_DIR / "koala_kombat_kruisin_status.json"
DEFAULT_WIFI_SECONDS = float(os.getenv("KOALA_KOMBAT_WIFI_SECONDS", "10"))
DEFAULT_BLE_SECONDS = float(os.getenv("KOALA_KOMBAT_BLE_SECONDS", "10"))
DEFAULT_MAX_RECORDS = int(os.getenv("KOALA_KOMBAT_MAX_RECORDS", "10000"))
WIGLE_UPLOAD_URL = os.getenv("WIGLE_UPLOAD_URL", "https://api.wigle.net/api/v2/file/upload")

GPS_ENABLE_ENV = "KOALA_KOMBAT_GPS_LOGGING"
WIGLE_UPLOAD_ENABLE_ENV = "KOALA_KOMBAT_WIGLE_UPLOAD"
WIGLE_API_NAME_ENV = os.getenv("KOALA_KOMBAT_WIGLE_API_NAME_ENV", "WIGLE_API_NAME")
WIGLE_API_TOKEN_ENV = os.getenv("KOALA_KOMBAT_WIGLE_API_TOKEN_ENV", "WIGLE_API_TOKEN")


@dataclass(frozen=True)
class SurveyRecord:
    radio: str
    identifier: str
    name: str
    rssi: Optional[int]
    channel: str = ""
    frequency_mhz: str = ""
    security: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_meters: Optional[float] = None
    accuracy_meters: Optional[float] = None
    location_source: str = "none"
    first_seen: str = ""
    source: str = DISPLAY_NAME
    safety_scope: str = "passive Wi-Fi/BLE survey observation only; no association, pairing, probing, deauth, spoofing, jamming, or access workflow"


@dataclass(frozen=True)
class SurveyResult:
    status: str
    mode: str
    wifi_records: int
    ble_records: int
    records_with_location: int
    output_jsonl_path: str
    wifi_csv_path: str
    ble_csv_path: str
    geojson_path: str
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_status(payload: dict[str, object], path: Path = DEFAULT_STATUS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _fixed_env_fix() -> Optional[dict[str, object]]:
    lat = _safe_float(os.getenv("KOALA_KOMBAT_FIXED_LAT") or os.getenv("KOALABYTE_GNSS_LAT"))
    lon = _safe_float(os.getenv("KOALA_KOMBAT_FIXED_LON") or os.getenv("KOALABYTE_GNSS_LON"))
    if not valid_lat_lon(lat, lon):
        return None
    return {
        "latitude": lat,
        "longitude": lon,
        "altitude_meters": _safe_float(os.getenv("KOALA_KOMBAT_FIXED_ALT") or os.getenv("KOALABYTE_GNSS_ALT")),
        "accuracy_meters": _safe_float(os.getenv("KOALA_KOMBAT_FIXED_ACCURACY") or os.getenv("KOALABYTE_GNSS_ACCURACY")) or 25.0,
        "source": "koala_kombat_fixed_env",
        "status": "fix",
    }


def survey_location_fix() -> Optional[dict[str, object]]:
    fixed = _fixed_env_fix()
    if fixed:
        return fixed
    if not _truthy(os.getenv(GPS_ENABLE_ENV)):
        return None
    fix = current_fix(authorized=True, prompt=False)
    return asdict(fix) if fix is not None else None


def _location_tuple(fix: Optional[dict[str, object]]) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float], str]:
    if not fix:
        return None, None, None, None, "none"
    lat = _safe_float(fix.get("latitude"))
    lon = _safe_float(fix.get("longitude"))
    if not valid_lat_lon(lat, lon):
        return None, None, None, None, "none"
    return lat, lon, _safe_float(fix.get("altitude_meters")), _safe_float(fix.get("accuracy_meters")), str(fix.get("source", "current_fix"))


def _split_nmcli(line: str) -> list[str]:
    fields: list[str] = []
    buf: list[str] = []
    escaped = False
    for char in line:
        if escaped:
            buf.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(buf))
            buf = []
        else:
            buf.append(char)
    fields.append("".join(buf))
    return fields


def _scan_wifi_nmcli(fix: Optional[dict[str, object]]) -> tuple[list[SurveyRecord], list[str]]:
    notes: list[str] = []
    if not shutil.which("nmcli"):
        return [], ["nmcli not installed; Wi-Fi survey falls back to iw if available."]
    try:
        result = subprocess.run(
            ["nmcli", "-t", "--escape", "yes", "-f", "SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"],
            capture_output=True,
            text=True,
            timeout=max(8.0, DEFAULT_WIFI_SECONDS),
            check=False,
        )
    except Exception as exc:
        return [], [f"nmcli Wi-Fi survey failed: {exc}"]
    if result.returncode != 0:
        notes.append((result.stderr or result.stdout or "nmcli returned non-zero status").strip()[:240])
    lat, lon, alt, acc, source = _location_tuple(fix)
    records: list[SurveyRecord] = []
    seen: set[str] = set()
    for line in (result.stdout or "").splitlines():
        parts = _split_nmcli(line)
        if len(parts) < 6:
            continue
        ssid, bssid, channel, freq, signal, security = parts[:6]
        bssid = bssid.strip()
        if not bssid or bssid in seen:
            continue
        seen.add(bssid)
        records.append(SurveyRecord(
            radio="wifi",
            identifier=bssid,
            name=ssid.strip(),
            rssi=_safe_int(signal),
            channel=channel.strip(),
            frequency_mhz=freq.strip(),
            security=security.strip(),
            latitude=lat,
            longitude=lon,
            altitude_meters=alt,
            accuracy_meters=acc,
            location_source=source,
            first_seen=_utc_now(),
        ))
    return records, notes


def _scan_wifi_iw(fix: Optional[dict[str, object]]) -> tuple[list[SurveyRecord], list[str]]:
    notes: list[str] = []
    if not shutil.which("iw"):
        return [], ["iw not installed; no Wi-Fi fallback scan available."]
    try:
        dev_result = subprocess.run(["iw", "dev"], capture_output=True, text=True, timeout=5, check=False)
    except Exception as exc:
        return [], [f"iw dev failed: {exc}"]
    interfaces = re.findall(r"Interface\s+(\S+)", dev_result.stdout or "")
    if not interfaces:
        return [], ["iw found no Wi-Fi interface."]
    lat, lon, alt, acc, source = _location_tuple(fix)
    all_records: list[SurveyRecord] = []
    for iface in interfaces[:2]:
        try:
            scan = subprocess.run(["iw", "dev", iface, "scan"], capture_output=True, text=True, timeout=max(10.0, DEFAULT_WIFI_SECONDS), check=False)
        except Exception as exc:
            notes.append(f"iw scan failed on {iface}: {exc}")
            continue
        current: dict[str, str] = {}
        for raw in (scan.stdout or "").splitlines():
            line = raw.strip()
            if line.startswith("BSS "):
                if current.get("bssid"):
                    all_records.append(_iw_record(current, lat, lon, alt, acc, source))
                current = {"bssid": line.split()[1].split("(")[0]}
            elif line.startswith("SSID:"):
                current["ssid"] = line.split(":", 1)[1].strip()
            elif line.startswith("freq:"):
                current["freq"] = line.split(":", 1)[1].strip()
            elif line.startswith("signal:"):
                current["rssi"] = line.split(":", 1)[1].replace("dBm", "").strip()
            elif "DS Parameter set: channel" in line:
                current["channel"] = line.rsplit(" ", 1)[-1]
            elif line in {"WPA:", "RSN:"}:
                current["security"] = "WPA/RSN"
        if current.get("bssid"):
            all_records.append(_iw_record(current, lat, lon, alt, acc, source))
    return all_records, notes


def _iw_record(data: dict[str, str], lat: Optional[float], lon: Optional[float], alt: Optional[float], acc: Optional[float], source: str) -> SurveyRecord:
    return SurveyRecord(
        radio="wifi",
        identifier=data.get("bssid", ""),
        name=data.get("ssid", ""),
        rssi=_safe_int(data.get("rssi")),
        channel=data.get("channel", ""),
        frequency_mhz=data.get("freq", ""),
        security=data.get("security", ""),
        latitude=lat,
        longitude=lon,
        altitude_meters=alt,
        accuracy_meters=acc,
        location_source=source,
        first_seen=_utc_now(),
    )


def scan_wifi(fix: Optional[dict[str, object]]) -> tuple[list[SurveyRecord], list[str]]:
    records, notes = _scan_wifi_nmcli(fix)
    if records:
        return records, notes
    fallback_records, fallback_notes = _scan_wifi_iw(fix)
    return fallback_records, notes + fallback_notes


async def _scan_ble_async(fix: Optional[dict[str, object]], duration_seconds: float) -> tuple[list[SurveyRecord], list[str]]:
    notes: list[str] = []
    try:
        from bleak import BleakScanner  # type: ignore
    except Exception as exc:
        return [], [f"bleak unavailable; BLE survey skipped: {exc}"]
    lat, lon, alt, acc, source = _location_tuple(fix)
    records: list[SurveyRecord] = []
    try:
        found = await BleakScanner.discover(timeout=max(1.0, duration_seconds), return_adv=True)
    except TypeError:
        devices = await BleakScanner.discover(timeout=max(1.0, duration_seconds))
        found = {getattr(device, "address", ""): (device, None) for device in devices}
    except Exception as exc:
        return [], [f"BLE survey failed: {exc}"]
    for address, payload in found.items():
        if isinstance(payload, tuple):
            device = payload[0]
            adv = payload[1] if len(payload) > 1 else None
        else:
            device = payload
            adv = None
        identifier = str(getattr(device, "address", address) or address).strip()
        if not identifier:
            continue
        name = str(getattr(device, "name", "") or getattr(adv, "local_name", "") or "").strip()
        rssi = _safe_int(getattr(adv, "rssi", None) if adv is not None else getattr(device, "rssi", None))
        records.append(SurveyRecord(
            radio="ble",
            identifier=identifier,
            name=name,
            rssi=rssi,
            latitude=lat,
            longitude=lon,
            altitude_meters=alt,
            accuracy_meters=acc,
            location_source=source,
            first_seen=_utc_now(),
        ))
    return records, notes


def scan_ble(fix: Optional[dict[str, object]], duration_seconds: float = DEFAULT_BLE_SECONDS) -> tuple[list[SurveyRecord], list[str]]:
    try:
        return asyncio.run(_scan_ble_async(fix, duration_seconds))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_scan_ble_async(fix, duration_seconds))
        finally:
            loop.close()


def _wigle_row(record: SurveyRecord) -> Optional[dict[str, object]]:
    if not valid_lat_lon(record.latitude, record.longitude):
        return None
    return {
        "MAC": record.identifier,
        "SSID": record.name,
        "AuthMode": record.security if record.radio == "wifi" else "[BLE]",
        "FirstSeen": record.first_seen,
        "Channel": record.channel,
        "RSSI": record.rssi if record.rssi is not None else "",
        "CurrentLatitude": record.latitude,
        "CurrentLongitude": record.longitude,
        "AltitudeMeters": record.altitude_meters or "",
        "AccuracyMeters": record.accuracy_meters or "",
        "Type": "WIFI" if record.radio == "wifi" else "BLE",
    }


def _write_csv(path: Path, records: Iterable[SurveyRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["radio", "identifier", "name", "rssi", "channel", "frequency_mhz", "security", "latitude", "longitude", "altitude_meters", "accuracy_meters", "location_source", "first_seen", "source", "safety_scope"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def _write_geojson(path: Path, records: Iterable[SurveyRecord]) -> int:
    features: list[dict[str, object]] = []
    for record in records:
        if not valid_lat_lon(record.latitude, record.longitude):
            continue
        payload = asdict(record)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [record.longitude, record.latitude]},
            "properties": payload,
        })
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=2, sort_keys=True), encoding="utf-8")
    return len(features)


def _write_wigle_csv(path: Path, records: Iterable[SurveyRecord]) -> int:
    rows = [row for row in (_wigle_row(record) for record in records) if row is not None]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("WigleWifi-1.4,appRelease=KoalaByteBlue,model=KoalaByteBlue,release=Main,device=KoalaByteBlue,display=KoalaKombatKruisin,board=RaspberryPi3B\n")
        writer = csv.DictWriter(handle, fieldnames=["MAC", "SSID", "AuthMode", "FirstSeen", "Channel", "RSSI", "CurrentLatitude", "CurrentLongitude", "AltitudeMeters", "AccuracyMeters", "Type"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return len(rows)


def run_survey(*, mode: str = "both", wifi_seconds: float = DEFAULT_WIFI_SECONDS, ble_seconds: float = DEFAULT_BLE_SECONDS, output_dir: Path = DEFAULT_OUTPUT_DIR, max_records: int = DEFAULT_MAX_RECORDS) -> SurveyResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    jsonl_path = output_dir / f"koala_kombat_kruisin_{stamp}.jsonl"
    wifi_csv_path = output_dir / f"koala_kombat_kruisin_wifi_{stamp}.csv"
    ble_csv_path = output_dir / f"koala_kombat_kruisin_ble_{stamp}.csv"
    geojson_path = output_dir / f"koala_kombat_kruisin_{stamp}.geojson"
    wigle_csv_path = output_dir / f"koala_kombat_kruisin_wigle_{stamp}.csv"

    fix = survey_location_fix()
    notes: list[str] = []
    if fix is None:
        notes.append(f"GPS enrichment disabled or unavailable. Set {GPS_ENABLE_ENV}=1 with a working GNSS path, or use KOALA_KOMBAT_FIXED_LAT/LON for a lab coordinate.")

    wifi_records: list[SurveyRecord] = []
    ble_records: list[SurveyRecord] = []
    normalized_mode = mode.lower().strip()
    if normalized_mode in {"both", "wifi", "wi-fi"}:
        wifi_records, wifi_notes = scan_wifi(fix)
        notes.extend(wifi_notes)
    if normalized_mode in {"both", "ble", "bluetooth"}:
        ble_records, ble_notes = scan_ble(fix, duration_seconds=ble_seconds)
        notes.extend(ble_notes)

    records = (wifi_records + ble_records)[:max_records]
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
    _write_csv(wifi_csv_path, wifi_records)
    _write_csv(ble_csv_path, ble_records)
    geo_count = _write_geojson(geojson_path, records)
    wigle_count = _write_wigle_csv(wigle_csv_path, records)

    status = "KOALA_KOMBAT_KRUISIN_READY" if records else "KOALA_KOMBAT_KRUISIN_EMPTY"
    result = SurveyResult(
        status=status,
        mode=normalized_mode,
        wifi_records=len(wifi_records),
        ble_records=len(ble_records),
        records_with_location=max(geo_count, wigle_count),
        output_jsonl_path=str(jsonl_path),
        wifi_csv_path=str(wifi_csv_path),
        ble_csv_path=str(ble_csv_path),
        geojson_path=str(geojson_path),
        wigle_csv_path=str(wigle_csv_path),
        status_path=str(DEFAULT_STATUS_PATH),
        gps_source=str(fix.get("source", "none")) if fix else "none",
        notes=notes,
    )
    _write_status(asdict(result) | {"updated_at": time.time(), "wigle_upload_enabled": _truthy(os.getenv(WIGLE_UPLOAD_ENABLE_ENV)), "wigle_credentials_configured": bool(os.getenv(WIGLE_API_NAME_ENV) and os.getenv(WIGLE_API_TOKEN_ENV))})
    return result


def status() -> dict[str, object]:
    fix = survey_location_fix()
    payload = {
        "status": "KOALA_KOMBAT_KRUISIN_STATUS",
        "display_name": DISPLAY_NAME,
        "wifi_scanner_available": bool(shutil.which("nmcli") or shutil.which("iw")),
        "ble_scanner_dependency": "bleak",
        "gps_logging_enabled_env": GPS_ENABLE_ENV,
        "gps_logging_enabled": _truthy(os.getenv(GPS_ENABLE_ENV)) or _fixed_env_fix() is not None,
        "gps_fix_available": fix is not None,
        "gps_source": str(fix.get("source", "none")) if fix else "none",
        "wigle_upload_enabled_env": WIGLE_UPLOAD_ENABLE_ENV,
        "wigle_upload_enabled": _truthy(os.getenv(WIGLE_UPLOAD_ENABLE_ENV)),
        "wigle_api_name_env": WIGLE_API_NAME_ENV,
        "wigle_api_token_env": WIGLE_API_TOKEN_ENV,
        "wigle_credentials_configured": bool(os.getenv(WIGLE_API_NAME_ENV) and os.getenv(WIGLE_API_TOKEN_ENV)),
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "safety_scope": "Authorized passive Wi-Fi/BLE RF site survey only. WiGLE upload is blocked unless explicitly armed.",
        "updated_at": time.time(),
    }
    _write_status(payload)
    return payload


def upload_to_wigle(*, dry_run: bool = False, mode: str = "both") -> dict[str, object]:
    survey = run_survey(mode=mode)
    payload = asdict(survey) | {"upload_url": WIGLE_UPLOAD_URL, "dry_run": dry_run}
    if survey.records_with_location <= 0:
        payload.update({"status": "KOALA_KOMBAT_WIGLE_UPLOAD_BLOCKED", "reason": "No Wi-Fi/BLE survey records with latitude/longitude were available."})
        _write_status(payload)
        return payload
    if dry_run:
        payload.update({"status": "KOALA_KOMBAT_WIGLE_UPLOAD_DRY_RUN", "reason": "WiGLE CSV built but network upload was not attempted."})
        _write_status(payload)
        return payload
    if not _truthy(os.getenv(WIGLE_UPLOAD_ENABLE_ENV)):
        payload.update({"status": "KOALA_KOMBAT_WIGLE_UPLOAD_BLOCKED", "reason": f"Set {WIGLE_UPLOAD_ENABLE_ENV}=1 to arm WiGLE upload."})
        _write_status(payload)
        return payload
    api_name = os.getenv(WIGLE_API_NAME_ENV)
    api_token = os.getenv(WIGLE_API_TOKEN_ENV)
    if not api_name or not api_token:
        payload.update({"status": "KOALA_KOMBAT_WIGLE_UPLOAD_BLOCKED", "reason": f"Missing {WIGLE_API_NAME_ENV}/{WIGLE_API_TOKEN_ENV}."})
        _write_status(payload)
        return payload
    try:
        import requests  # type: ignore
        with Path(survey.wigle_csv_path).open("rb") as handle:
            response = requests.post(WIGLE_UPLOAD_URL, auth=(api_name, api_token), files={"file": (Path(survey.wigle_csv_path).name, handle, "text/csv")}, data={"donate": "on"}, timeout=60)
        payload.update({"status": "KOALA_KOMBAT_WIGLE_UPLOAD_COMPLETE" if response.ok else "KOALA_KOMBAT_WIGLE_UPLOAD_FAILED", "http_status": response.status_code, "response_text": response.text[:1000]})
    except Exception as exc:
        payload.update({"status": "KOALA_KOMBAT_WIGLE_UPLOAD_FAILED", "error": str(exc)})
    _write_status(payload)
    return payload


def control(action: str, *, dry_run: bool = False) -> dict[str, object]:
    normalized = action.lower().strip()
    if normalized == "status":
        return status()
    if normalized in {"survey", "both"}:
        return asdict(run_survey(mode="both"))
    if normalized in {"wifi-survey", "wifi", "wi-fi"}:
        return asdict(run_survey(mode="wifi"))
    if normalized in {"ble-survey", "ble", "bluetooth"}:
        return asdict(run_survey(mode="ble"))
    if normalized in {"gps-status", "gps"}:
        fix = survey_location_fix()
        return {"status": "KOALA_KOMBAT_GPS_READY" if fix else "KOALA_KOMBAT_GPS_NOT_READY", "fix": fix, "gps_logging_enabled_env": GPS_ENABLE_ENV}
    if normalized in {"export", "exports"}:
        return asdict(run_survey(mode="both"))
    if normalized in {"wigle-upload", "upload"}:
        return upload_to_wigle(dry_run=dry_run)
    return {"status": "KOALA_KOMBAT_UNKNOWN_ACTION", "action": action}
