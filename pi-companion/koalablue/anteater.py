from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

ACTION_ID = "anteater"
ACTION_NAME = "AntEater"
DEFAULT_OUTPUT_DIR = Path("logs/anteater")
DEFAULT_STATUS_PATH = Path("logs/anteater/anteater_status.json")
DEFAULT_SCAN_SECONDS = 15.0

PAYMENT_NAME_MARKERS = {
    "skimmer",
    "card",
    "credit",
    "debit",
    "stripe",
    "magstripe",
    "msr",
    "reader",
    "pos",
    "pump",
    "fuel",
    "atm",
}

GENERIC_UART_MARKERS = {
    "hc-05",
    "hc05",
    "hc-06",
    "hc06",
    "hm-10",
    "hm10",
    "hmsoft",
    "bt05",
    "mlt-bt05",
    "cc254",
    "ble_uart",
    "uart",
    "serial",
}

GENERIC_UART_SERVICE_UUIDS = {
    "0000ffe0-0000-1000-8000-00805f9b34fb",
    "0000ffe1-0000-1000-8000-00805f9b34fb",
    "6e400001-b5a3-f393-e0a9-e50e24dcca9e",
    "6e400002-b5a3-f393-e0a9-e50e24dcca9e",
    "6e400003-b5a3-f393-e0a9-e50e24dcca9e",
}


@dataclass
class AntEaterObservation:
    address: str
    name: str = ""
    rssi: Optional[int] = None
    service_uuids: list[str] = field(default_factory=list)
    manufacturer_ids: list[str] = field(default_factory=list)
    risk_score: int = 0
    risk_level: str = "low"
    indicators: list[str] = field(default_factory=list)


@dataclass
class AntEaterReport:
    action_id: str
    action_name: str
    status: str
    started_at: float
    ended_at: float
    scan_seconds: float
    source: str
    device_count: int
    suspect_count: int
    observations: list[AntEaterObservation]
    artifacts: dict[str, str]
    safety: dict[str, object]
    notes: list[str]


def _hash_address(address: str) -> str:
    clean = address.strip().lower()
    if not clean:
        return "unknown"
    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:12]
    return f"redacted-{digest}"


def _risk_level(score: int) -> str:
    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _normalize_uuid(value: object) -> str:
    return str(value).strip().lower()


def _manufacturer_ids(data: object) -> list[str]:
    if isinstance(data, dict):
        return [str(key) for key in sorted(data.keys(), key=str)]
    return []


def assess_observation(raw: dict[str, Any], raw_addresses: bool = False) -> AntEaterObservation:
    name = str(raw.get("name") or raw.get("local_name") or "").strip()
    address = str(raw.get("address") or raw.get("mac") or raw.get("id") or "unknown")
    rssi_value = raw.get("rssi")
    try:
        rssi = int(rssi_value) if rssi_value is not None else None
    except (TypeError, ValueError):
        rssi = None

    service_uuids = [_normalize_uuid(uuid) for uuid in raw.get("service_uuids", []) or []]
    manufacturer_data = raw.get("manufacturer_data", {})
    indicators: list[str] = []
    score = 0
    lower_name = name.lower()

    if any(marker in lower_name for marker in PAYMENT_NAME_MARKERS):
        indicators.append("payment or magstripe term in BLE name")
        score += 4
    if any(marker in lower_name for marker in GENERIC_UART_MARKERS):
        indicators.append("generic BLE serial/UART module name")
        score += 3
    if any(uuid in GENERIC_UART_SERVICE_UUIDS for uuid in service_uuids):
        indicators.append("generic BLE UART service UUID advertised")
        score += 2
    if not name:
        indicators.append("no advertised device name")
        score += 1
    if rssi is not None and rssi >= -55:
        indicators.append("strong nearby signal")
        score += 1
    if rssi is not None and rssi >= -55 and (not name or any(marker in lower_name for marker in GENERIC_UART_MARKERS)):
        indicators.append("nearby unnamed/generic module pattern")
        score += 2
    if manufacturer_data and not service_uuids and not name:
        indicators.append("manufacturer data with no readable identity")
        score += 1

    display_address = address if raw_addresses else _hash_address(address)
    return AntEaterObservation(
        address=display_address,
        name=name or "(unnamed)",
        rssi=rssi,
        service_uuids=service_uuids,
        manufacturer_ids=_manufacturer_ids(manufacturer_data),
        risk_score=score,
        risk_level=_risk_level(score),
        indicators=indicators,
    )


def _observation_from_bleak(address: str, device: object, advertisement: object | None, raw_addresses: bool) -> AntEaterObservation:
    name = getattr(device, "name", "") or getattr(advertisement, "local_name", "") or ""
    rssi = getattr(advertisement, "rssi", None)
    if rssi is None:
        rssi = getattr(device, "rssi", None)
    service_uuids = list(getattr(advertisement, "service_uuids", []) or []) if advertisement is not None else []
    manufacturer_data = getattr(advertisement, "manufacturer_data", {}) if advertisement is not None else {}
    return assess_observation(
        {
            "address": address or getattr(device, "address", "unknown"),
            "name": name,
            "rssi": rssi,
            "service_uuids": service_uuids,
            "manufacturer_data": manufacturer_data,
        },
        raw_addresses=raw_addresses,
    )


async def _scan_bleak(scan_seconds: float, raw_addresses: bool) -> tuple[list[AntEaterObservation], Optional[str]]:
    try:
        from bleak import BleakScanner  # type: ignore
    except Exception as exc:
        return [], f"BLEAK unavailable: {exc}"

    try:
        discovered = await BleakScanner.discover(timeout=scan_seconds, return_adv=True)
    except TypeError:
        try:
            devices = await BleakScanner.discover(timeout=scan_seconds)
            return [
                assess_observation(
                    {
                        "address": getattr(device, "address", "unknown"),
                        "name": getattr(device, "name", "") or "",
                        "rssi": getattr(device, "rssi", None),
                        "service_uuids": [],
                        "manufacturer_data": {},
                    },
                    raw_addresses=raw_addresses,
                )
                for device in devices
            ], None
        except Exception as exc:
            return [], f"BLEAK scan failed: {exc}"
    except Exception as exc:
        return [], f"BLEAK scan failed: {exc}"

    observations: list[AntEaterObservation] = []
    if isinstance(discovered, dict):
        for address, pair in discovered.items():
            try:
                device, advertisement = pair
            except Exception:
                device, advertisement = pair, None
            observations.append(_observation_from_bleak(str(address), device, advertisement, raw_addresses))
    return observations, None


def _load_observations_from_file(path: Path, raw_addresses: bool) -> list[AntEaterObservation]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    records: list[dict[str, Any]] = []
    try:
        loaded = json.loads(text)
        if isinstance(loaded, list):
            records = [item for item in loaded if isinstance(item, dict)]
        elif isinstance(loaded, dict):
            for key in ("observations", "devices", "records", "results"):
                value = loaded.get(key)
                if isinstance(value, list):
                    records = [item for item in value if isinstance(item, dict)]
                    break
            if not records:
                records = [loaded]
    except json.JSONDecodeError:
        for line in text.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append(item)
    return [assess_observation(record, raw_addresses=raw_addresses) for record in records]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_markdown(path: Path, report: AntEaterReport) -> None:
    lines = [
        "# AntEater BLE Card Skimmer Detector Report",
        "",
        f"Status: **{report.status}**",
        f"Devices reviewed: **{report.device_count}**",
        f"Suspect devices: **{report.suspect_count}**",
        "",
        "AntEater is advertisement-only. It does not pair, connect, write, replay, spoof, jam, or interfere with nearby devices.",
        "",
        "## Findings",
    ]
    suspects = [obs for obs in report.observations if obs.risk_level in {"medium", "high"}]
    if not suspects:
        lines.append("No medium/high-risk BLE advertisement patterns were found in this run.")
    for obs in suspects:
        lines.extend(
            [
                f"- **{obs.risk_level.upper()}** `{obs.name}` `{obs.address}` RSSI={obs.rssi} score={obs.risk_score}",
                f"  - Indicators: {', '.join(obs.indicators) if obs.indicators else 'none'}",
            ]
        )
    lines.extend(
        [
            "",
            "## Operator next steps",
            "1. Treat this as a triage signal, not proof of a skimmer.",
            "2. Inspect the physical payment terminal or fuel pump only if you own it or have authorization.",
            "3. Preserve the report and escalate through the site owner, bank, or law enforcement as appropriate.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_once(
    scan_seconds: float = DEFAULT_SCAN_SECONDS,
    input_file: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    status_path: str | Path = DEFAULT_STATUS_PATH,
    raw_addresses: bool = False,
) -> AntEaterReport:
    started = time.time()
    notes: list[str] = []
    source = "bleak-scan"
    if input_file:
        source = str(input_file)
        observations = _load_observations_from_file(Path(input_file), raw_addresses=raw_addresses)
    else:
        observations, error = asyncio.run(_scan_bleak(float(scan_seconds), raw_addresses=raw_addresses))
        if error:
            notes.append(error)

    observations.sort(key=lambda obs: (obs.risk_score, obs.rssi if obs.rssi is not None else -999), reverse=True)
    suspect_count = sum(1 for obs in observations if obs.risk_level in {"medium", "high"})
    ended = time.time()
    output_path = Path(output_dir)
    stamp = int(started)
    json_path = output_path / f"anteater_report_{stamp}.json"
    md_path = output_path / f"anteater_report_{stamp}.md"
    status = "SUSPECT_PATTERN_FOUND" if suspect_count else ("NO_SUSPECT_PATTERN" if observations else "NO_DATA")
    report = AntEaterReport(
        action_id=ACTION_ID,
        action_name=ACTION_NAME,
        status=status,
        started_at=started,
        ended_at=ended,
        scan_seconds=float(scan_seconds),
        source=source,
        device_count=len(observations),
        suspect_count=suspect_count,
        observations=observations,
        artifacts={"json_report": str(json_path), "markdown_report": str(md_path), "status": str(status_path)},
        safety={
            "authorized_lab_or_defensive_use_only": True,
            "advertisement_only": True,
            "bleak_scan_only": True,
            "pairing": False,
            "connections": False,
            "writes": False,
            "spoofing": False,
            "jamming": False,
            "packet_replay": False,
            "raw_addresses_default": False,
        },
        notes=notes,
    )
    _write_json(json_path, asdict(report))
    _write_markdown(md_path, report)
    _write_json(Path(status_path), {"status": status, "updated_at": ended, "suspect_count": suspect_count, "device_count": len(observations), "latest_report": str(json_path)})
    return report


def render_summary(report: AntEaterReport) -> str:
    lines = [
        "== AntEater BLE Card Skimmer Detector ==",
        f"Status: {report.status}",
        f"Devices reviewed: {report.device_count}",
        f"Suspect patterns: {report.suspect_count}",
    ]
    if report.notes:
        lines.append("Notes: " + "; ".join(report.notes))
    for obs in report.observations[:8]:
        indicator_text = ", ".join(obs.indicators) if obs.indicators else "no skimmer indicators"
        lines.append(f"- {obs.risk_level.upper()} score={obs.risk_score} rssi={obs.rssi} name={obs.name} id={obs.address}: {indicator_text}")
    lines.append(f"JSON report: {report.artifacts['json_report']}")
    lines.append(f"Markdown report: {report.artifacts['markdown_report']}")
    return "\n".join(lines)


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="AntEater BLE card skimmer detector: passive advertisement-only triage")
    parser.add_argument("command", nargs="?", default="scan", choices=["scan", "analyze", "status"], help="Run a BLEAK scan, analyze an existing JSON/JSONL file, or show latest status")
    parser.add_argument("--scan-seconds", type=float, default=DEFAULT_SCAN_SECONDS)
    parser.add_argument("--input-json", default=None, help="JSON or JSONL file with BLE observations to analyze offline")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--status-path", default=str(DEFAULT_STATUS_PATH))
    parser.add_argument("--raw-addresses", action="store_true", help="Store raw BLE addresses in reports. Default stores hashed/redacted identifiers.")
    args = parser.parse_args()

    if args.command == "status":
        path = Path(args.status_path)
        print(path.read_text(encoding="utf-8") if path.exists() else "AntEater has not run yet.")
        return 0

    input_file = args.input_json if args.command == "analyze" else None
    report = run_once(scan_seconds=args.scan_seconds, input_file=input_file, output_dir=args.output_dir, status_path=args.status_path, raw_addresses=args.raw_addresses)
    print(render_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
