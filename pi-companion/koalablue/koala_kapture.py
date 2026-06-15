from __future__ import annotations

import asyncio
import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from bleak import BleakScanner
except Exception:  # pragma: no cover - allows import on non-BLE hosts
    BleakScanner = None  # type: ignore


@dataclass
class KoalaKaptureConfig:
    """Passive BLE metadata recorder for authorized lab work.

    Koala Kapture records advertisement metadata only. It does not connect,
    pair, write, disrupt, or transmit. Captures can be replayed locally through
    Koala Kry for parser, UI, report, eucalyptus, and XP testing.
    """

    output_dir: str = "/blecaptures/koala_kapture"
    duration_seconds: float = 30.0
    scan_window_seconds: float = 5.0
    target_name: Optional[str] = None
    target_address: Optional[str] = None
    max_records: int = 1000
    include_manufacturer_data: bool = True
    include_service_data: bool = True
    authorized_only: bool = True


@dataclass
class CapturedBleMetadata:
    record_type: str
    timestamp: float
    address: str
    name: str
    rssi: int
    local_name: str = ""
    service_uuids: List[str] = field(default_factory=list)
    manufacturer_data: Dict[str, str] = field(default_factory=dict)
    service_data: Dict[str, str] = field(default_factory=dict)
    tx_power: Optional[int] = None
    source: str = "Koala Kapture"
    safety_scope: str = "authorized BLE metadata capture only"


@dataclass
class KoalaKaptureResult:
    action: str
    started_at: float
    ended_at: float
    records: int
    unique_addresses: int
    jsonl_path: str
    csv_path: str
    manifest_path: str


def _bytes_to_hex(value: Any) -> str:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, bytearray):
        return bytes(value).hex()
    return str(value)


def _serialize_manufacturer_data(data: Any) -> Dict[str, str]:
    if not data:
        return {}
    return {str(key): _bytes_to_hex(value) for key, value in dict(data).items()}


def _serialize_service_data(data: Any) -> Dict[str, str]:
    if not data:
        return {}
    return {str(key): _bytes_to_hex(value) for key, value in dict(data).items()}


class KoalaKaptureRecorder:
    def __init__(self, config: Optional[KoalaKaptureConfig] = None) -> None:
        self.config = config or KoalaKaptureConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def record(self) -> KoalaKaptureResult:
        if BleakScanner is None:
            raise RuntimeError("bleak is not available; install requirements on the Raspberry Pi first")

        started = time.time()
        records: List[CapturedBleMetadata] = []
        deadline = started + self.config.duration_seconds

        while time.time() < deadline and len(records) < self.config.max_records:
            timeout = min(self.config.scan_window_seconds, max(0.5, deadline - time.time()))
            devices = await BleakScanner.discover(timeout=timeout, return_adv=True)  # type: ignore[union-attr]
            for _, pair in devices.items():
                if len(records) >= self.config.max_records:
                    break
                device, adv = pair
                name = device.name or getattr(adv, "local_name", None) or ""
                address = device.address
                if not self._matches_filter(name=name, address=address):
                    continue
                tx_power = getattr(adv, "tx_power", None)
                record = CapturedBleMetadata(
                    record_type="koala_kapture_ble_metadata",
                    timestamp=time.time(),
                    address=address,
                    name=name,
                    rssi=int(device.rssi),
                    local_name=getattr(adv, "local_name", None) or "",
                    service_uuids=list(getattr(adv, "service_uuids", []) or []),
                    manufacturer_data=_serialize_manufacturer_data(getattr(adv, "manufacturer_data", None)) if self.config.include_manufacturer_data else {},
                    service_data=_serialize_service_data(getattr(adv, "service_data", None)) if self.config.include_service_data else {},
                    tx_power=tx_power if isinstance(tx_power, int) else None,
                )
                records.append(record)

        ended = time.time()
        return self._write(records=records, started=started, ended=ended)

    def _matches_filter(self, *, name: str, address: str) -> bool:
        if self.config.target_address and address.lower() != self.config.target_address.lower():
            return False
        if self.config.target_name and self.config.target_name.lower() not in name.lower():
            return False
        return True

    def _write(self, *, records: List[CapturedBleMetadata], started: float, ended: float) -> KoalaKaptureResult:
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(started))
        jsonl_path = self.output_dir / f"koala_kapture_{stamp}.jsonl"
        csv_path = self.output_dir / f"koala_kapture_{stamp}.csv"
        manifest_path = self.output_dir / f"koala_kapture_{stamp}_manifest.json"

        with jsonl_path.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(asdict(record), sort_keys=True) + "\n")

        fieldnames = list(asdict(records[0]).keys()) if records else list(CapturedBleMetadata.__dataclass_fields__.keys())
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                row = asdict(record)
                for key in ("service_uuids", "manufacturer_data", "service_data"):
                    row[key] = json.dumps(row.get(key, {}), sort_keys=True)
                writer.writerow(row)

        manifest = {
            "action": "Koala Kapture",
            "mode": "passive_ble_metadata_capture",
            "rf_transmission": False,
            "started_at": started,
            "ended_at": ended,
            "records": len(records),
            "unique_addresses": len({r.address for r in records}),
            "jsonl_path": str(jsonl_path),
            "csv_path": str(csv_path),
            "safety_scope": "authorized BLE metadata capture only",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

        return KoalaKaptureResult(
            action="Koala Kapture",
            started_at=started,
            ended_at=ended,
            records=len(records),
            unique_addresses=manifest["unique_addresses"],
            jsonl_path=str(jsonl_path),
            csv_path=str(csv_path),
            manifest_path=str(manifest_path),
        )


def run_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Koala Kapture passive BLE metadata recorder")
    parser.add_argument("--output-dir", default="/blecaptures/koala_kapture")
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--scan-window-seconds", type=float, default=5.0)
    parser.add_argument("--target-name", default=None)
    parser.add_argument("--target-address", default=None)
    parser.add_argument("--max-records", type=int, default=1000)
    args = parser.parse_args()

    config = KoalaKaptureConfig(
        output_dir=args.output_dir,
        duration_seconds=args.duration_seconds,
        scan_window_seconds=args.scan_window_seconds,
        target_name=args.target_name,
        target_address=args.target_address,
        max_records=args.max_records,
    )
    result = asyncio.run(KoalaKaptureRecorder(config).record())
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
