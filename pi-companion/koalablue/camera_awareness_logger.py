#!/usr/bin/env python3
"""KoalaByte Blue camera awareness logger.

This module is intentionally manual/public-observation only. It stores rich
physical/public identifiers for cameras the operator personally observes or
learns about from public sources, without RF scanning, network probing, MAC/IP
collection, or avoidance routing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

LOG_ROOT = Path("logs/camera_awareness")
OBSERVATIONS_JSONL = "observations.jsonl"
REPORT_JSON = "camera_awareness_report.json"
REPORT_CSV = "camera_awareness_report.csv"

DISALLOWED_FIELD_HINTS = {
    "mac",
    "bssid",
    "ssid",
    "ip",
    "ipv4",
    "ipv6",
    "imei",
    "imsi",
    "bluetooth",
    "rf",
    "radio",
    "probe",
    "scan",
    "wardrive",
    "network_id",
    "wireless_id",
}

MAC_PATTERN = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")


@dataclass(frozen=True)
class CameraObservation:
    observation_id: str
    local_asset_id: str
    observed_at_utc: str
    label: str
    camera_type: str
    location_text: str
    latitude: Optional[float]
    longitude: Optional[float]
    confidence: str
    public_agency: str
    public_source_url: str
    visible_markings: str
    pole_or_mount_id: str
    public_asset_tag: str
    visible_make_model: str
    mounting_description: str
    facing_direction: str
    photo_reference: str
    notes: str
    safety_scope: str = "manual/public-observation only; no RF/network probing"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(*parts: object, length: int = 12) -> str:
    payload = "|".join(str(part or "").strip().lower() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def _check_text_is_manual_observation(field_name: str, value: object) -> None:
    text = str(value or "")
    if not text:
        return

    lowered_field = field_name.lower()
    lowered_text = text.lower()

    if any(token in lowered_field for token in DISALLOWED_FIELD_HINTS):
        raise ValueError(
            f"Refusing field '{field_name}': this logger does not store network, RF, scan, or probe identifiers."
        )

    if MAC_PATTERN.search(text):
        raise ValueError(
            f"Refusing field '{field_name}': MAC/BSSID-like identifiers are out of scope for this logger."
        )

    for chunk in re.split(r"[\s,;]+", text):
        candidate = chunk.strip("[](){}<>.,;:'\"")
        if not candidate:
            continue
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            pass
        else:
            raise ValueError(
                f"Refusing field '{field_name}': IP addresses are out of scope for this logger."
            )

    blocked_phrases = [
        "mac address",
        "bssid",
        "ssid",
        "ip address",
        "rf fingerprint",
        "bluetooth address",
        "network scan",
        "probe response",
        "avoidance route",
        "evasion",
    ]
    if any(phrase in lowered_text for phrase in blocked_phrases):
        raise ValueError(
            f"Refusing field '{field_name}': notes mention network/RF/evasion data that this logger cannot store."
        )


def _validate_lat_lon(latitude: Optional[float], longitude: Optional[float]) -> None:
    if latitude is not None and not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")
    if longitude is not None and not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")


def _validate_confidence(confidence: str) -> str:
    normalized = (confidence or "unknown").strip().lower()
    allowed = {"unknown", "low", "medium", "high"}
    if normalized not in allowed:
        raise ValueError(f"confidence must be one of: {', '.join(sorted(allowed))}")
    return normalized


def create_observation(
    *,
    label: str,
    camera_type: str = "unknown camera",
    location_text: str = "",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    confidence: str = "unknown",
    public_agency: str = "",
    public_source_url: str = "",
    visible_markings: str = "",
    pole_or_mount_id: str = "",
    public_asset_tag: str = "",
    visible_make_model: str = "",
    mounting_description: str = "",
    facing_direction: str = "",
    photo_reference: str = "",
    notes: str = "",
) -> CameraObservation:
    if not label.strip():
        raise ValueError("label is required")
    _validate_lat_lon(latitude, longitude)
    confidence = _validate_confidence(confidence)

    fields = {
        "label": label,
        "camera_type": camera_type,
        "location_text": location_text,
        "public_agency": public_agency,
        "public_source_url": public_source_url,
        "visible_markings": visible_markings,
        "pole_or_mount_id": pole_or_mount_id,
        "public_asset_tag": public_asset_tag,
        "visible_make_model": visible_make_model,
        "mounting_description": mounting_description,
        "facing_direction": facing_direction,
        "photo_reference": photo_reference,
        "notes": notes,
    }
    for key, value in fields.items():
        _check_text_is_manual_observation(key, value)

    observed_at = _utc_now()
    local_asset_id = "cam-" + _stable_hash(
        label,
        location_text,
        latitude,
        longitude,
        visible_markings,
        pole_or_mount_id,
        public_asset_tag,
        visible_make_model,
    )
    observation_id = "obs-" + _stable_hash(local_asset_id, observed_at, notes, length=16)

    return CameraObservation(
        observation_id=observation_id,
        local_asset_id=local_asset_id,
        observed_at_utc=observed_at,
        label=label.strip(),
        camera_type=(camera_type or "unknown camera").strip(),
        location_text=location_text.strip(),
        latitude=latitude,
        longitude=longitude,
        confidence=confidence,
        public_agency=public_agency.strip(),
        public_source_url=public_source_url.strip(),
        visible_markings=visible_markings.strip(),
        pole_or_mount_id=pole_or_mount_id.strip(),
        public_asset_tag=public_asset_tag.strip(),
        visible_make_model=visible_make_model.strip(),
        mounting_description=mounting_description.strip(),
        facing_direction=facing_direction.strip(),
        photo_reference=photo_reference.strip(),
        notes=notes.strip(),
    )


def _ensure_log_root(log_root: Path = LOG_ROOT) -> Path:
    log_root.mkdir(parents=True, exist_ok=True)
    return log_root


def append_observation(observation: CameraObservation, log_root: Path = LOG_ROOT) -> Path:
    root = _ensure_log_root(log_root)
    path = root / OBSERVATIONS_JSONL
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(observation), sort_keys=True) + "\n")
    return path


def load_observations(log_root: Path = LOG_ROOT) -> list[CameraObservation]:
    path = log_root / OBSERVATIONS_JSONL
    if not path.exists():
        return []
    rows: list[CameraObservation] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(CameraObservation(**json.loads(line)))
    return rows


def export_json(observations: Iterable[CameraObservation], log_root: Path = LOG_ROOT) -> Path:
    root = _ensure_log_root(log_root)
    path = root / REPORT_JSON
    data = [asdict(observation) for observation in observations]
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


def export_csv(observations: Iterable[CameraObservation], log_root: Path = LOG_ROOT) -> Path:
    root = _ensure_log_root(log_root)
    path = root / REPORT_CSV
    rows = [asdict(observation) for observation in observations]
    fieldnames = list(asdict(create_observation(label="schema-placeholder")).keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def build_summary(observations: list[CameraObservation]) -> dict[str, object]:
    by_type: dict[str, int] = {}
    by_confidence: dict[str, int] = {}
    for observation in observations:
        by_type[observation.camera_type] = by_type.get(observation.camera_type, 0) + 1
        by_confidence[observation.confidence] = by_confidence.get(observation.confidence, 0) + 1
    return {
        "count": len(observations),
        "by_type": by_type,
        "by_confidence": by_confidence,
        "scope": "manual/public-observation only; no RF/network probing",
    }


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--label", required=True, help="Local label, e.g. 'Main St pole camera'.")
    parser.add_argument("--type", default="unknown camera", dest="camera_type", help="Camera type label, e.g. 'ALPR-style camera'.")
    parser.add_argument("--location", default="", dest="location_text", help="Human-readable location/intersection.")
    parser.add_argument("--lat", type=float, default=None, dest="latitude")
    parser.add_argument("--lon", type=float, default=None, dest="longitude")
    parser.add_argument("--confidence", default="unknown", choices=["unknown", "low", "medium", "high"])
    parser.add_argument("--public-agency", default="")
    parser.add_argument("--public-source-url", default="")
    parser.add_argument("--visible-markings", default="", help="Visible physical markings observed from a lawful/public vantage point.")
    parser.add_argument("--pole-or-mount-id", default="", help="Visible pole/mount/utility asset marking, if publicly visible.")
    parser.add_argument("--public-asset-tag", default="", help="Publicly visible asset/permit tag, if any.")
    parser.add_argument("--visible-make-model", default="", help="Visible make/model from the housing/signage/public source, if known.")
    parser.add_argument("--mounting-description", default="", help="Physical mounting description, e.g. 'mast arm', 'wood utility pole'.")
    parser.add_argument("--facing-direction", default="", help="Observed camera direction, e.g. 'northbound'.")
    parser.add_argument("--photo-reference", default="", help="Local photo filename/reference. Do not include license plate or face data.")
    parser.add_argument("--notes", default="")
    parser.add_argument("--log-root", default=str(LOG_ROOT))


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue manual camera awareness logger")
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="Add one manual/public camera observation")
    _add_args(add_parser)

    list_parser = sub.add_parser("list", help="List stored observations")
    list_parser.add_argument("--log-root", default=str(LOG_ROOT))

    export_parser = sub.add_parser("export", help="Export observations")
    export_parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    export_parser.add_argument("--log-root", default=str(LOG_ROOT))

    sub.add_parser("schema", help="Show allowed fields and safety scope")

    args = parser.parse_args(argv)

    try:
        if args.command == "add":
            observation = create_observation(
                label=args.label,
                camera_type=args.camera_type,
                location_text=args.location_text,
                latitude=args.latitude,
                longitude=args.longitude,
                confidence=args.confidence,
                public_agency=args.public_agency,
                public_source_url=args.public_source_url,
                visible_markings=args.visible_markings,
                pole_or_mount_id=args.pole_or_mount_id,
                public_asset_tag=args.public_asset_tag,
                visible_make_model=args.visible_make_model,
                mounting_description=args.mounting_description,
                facing_direction=args.facing_direction,
                photo_reference=args.photo_reference,
                notes=args.notes,
            )
            path = append_observation(observation, Path(args.log_root))
            print(json.dumps({"saved_to": str(path), "observation": asdict(observation)}, indent=2, sort_keys=True))
            return 0

        if args.command == "list":
            observations = load_observations(Path(args.log_root))
            print(json.dumps({"summary": build_summary(observations), "observations": [asdict(o) for o in observations]}, indent=2, sort_keys=True))
            return 0

        if args.command == "export":
            observations = load_observations(Path(args.log_root))
            outputs: list[str] = []
            if args.format in {"json", "both"}:
                outputs.append(str(export_json(observations, Path(args.log_root))))
            if args.format in {"csv", "both"}:
                outputs.append(str(export_csv(observations, Path(args.log_root))))
            print(json.dumps({"exported": outputs, "summary": build_summary(observations)}, indent=2, sort_keys=True))
            return 0

        if args.command == "schema":
            fields = list(asdict(create_observation(label="example camera")).keys())
            print(json.dumps({
                "allowed_fields": fields,
                "blocked_data": sorted(DISALLOWED_FIELD_HINTS),
                "scope": "manual/public-observation only; no RF scanning, network probing, MAC/IP/BSSID collection, or evasion routing",
            }, indent=2, sort_keys=True))
            return 0
    except ValueError as exc:
        print(f"camera awareness logger refused input: {exc}")
        return 2

    return 1
