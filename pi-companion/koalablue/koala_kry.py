from __future__ import annotations

import csv
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class KoalaKryConfig:
    """Synthetic BLE log generator for parser/UI stress testing.

    Koala Kry does not transmit RF. It writes realistic-looking local test
    records so the companion UI, reports, eucalyptus import path, and leveling
    hooks can be tested without filling the air with BLE traffic.
    """

    output_dir: str = "logs/koala_kry"
    device_count: int = 40
    samples: int = 250
    min_rssi: int = -94
    max_rssi: int = -38
    include_named_lab_devices: bool = True
    xp_reward: int = 5


@dataclass
class SyntheticBleRecord:
    timestamp: float
    address: str
    name: str
    rssi: int
    connectable: bool
    source: str = "koala_kry_synthetic"
    note: str = "local synthetic test record; no RF transmission"


LAB_NAMES = [
    "EarTag-Lab",
    "KoalaBlue-Lab",
    "BenchBeacon-01",
    "LabSensor-A",
    "UrbanPoaching-Target",
]

GENERIC_NAMES = [
    "",
    "BLE-Test",
    "DevBoard",
    "EnvSensor",
    "LoggerNode",
    "BeaconSim",
    "LabPeripheral",
]


def random_static_address(rng: random.Random) -> str:
    first = rng.randint(0xC0, 0xFF)  # static random high bits set
    parts = [first] + [rng.randint(0, 255) for _ in range(5)]
    return ":".join(f"{p:02X}" for p in parts)


def build_device_pool(config: KoalaKryConfig, rng: random.Random) -> List[tuple[str, str]]:
    pool: List[tuple[str, str]] = []
    names: Iterable[str] = LAB_NAMES + GENERIC_NAMES if config.include_named_lab_devices else GENERIC_NAMES
    name_list = list(names)
    for i in range(config.device_count):
        base = rng.choice(name_list)
        if base and rng.random() < 0.55:
            name = f"{base}-{i:02d}"
        else:
            name = base
        pool.append((random_static_address(rng), name))
    return pool


def generate_records(config: Optional[KoalaKryConfig] = None, seed: Optional[int] = None) -> List[SyntheticBleRecord]:
    cfg = config or KoalaKryConfig()
    rng = random.Random(seed)
    pool = build_device_pool(cfg, rng)
    records: List[SyntheticBleRecord] = []
    now = time.time()
    for idx in range(cfg.samples):
        address, name = rng.choice(pool)
        rssi = rng.randint(cfg.min_rssi, cfg.max_rssi)
        # Add a slow wave so the synthetic data has movement-like variation.
        rssi = max(cfg.min_rssi, min(cfg.max_rssi, rssi + int(6 * rng.random()) - 3))
        records.append(
            SyntheticBleRecord(
                timestamp=now + idx * 0.25,
                address=address,
                name=name,
                rssi=rssi,
                connectable=bool(rng.getrandbits(1)),
            )
        )
    return records


def write_records(records: List[SyntheticBleRecord], output_dir: str | Path) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    jsonl_path = out / f"koala_kry_{stamp}.jsonl"
    csv_path = out / f"koala_kry_{stamp}.csv"
    summary_path = out / f"koala_kry_{stamp}_summary.json"

    with jsonl_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(asdict(rec), sort_keys=True) + "\n")

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(records[0]).keys()) if records else ["timestamp"])
        writer.writeheader()
        for rec in records:
            writer.writerow(asdict(rec))

    unique_addresses = len({rec.address for rec in records})
    named = sum(1 for rec in records if rec.name)
    summary = {
        "action": "Koala Kry",
        "mode": "synthetic_ble_log_generator",
        "rf_transmission": False,
        "records": len(records),
        "unique_addresses": unique_addresses,
        "named_records": named,
        "jsonl_path": str(jsonl_path),
        "csv_path": str(csv_path),
        "xp_reward": 5,
        "safety_scope": "local synthetic test data only",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def run_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Koala Kry synthetic BLE log generator")
    parser.add_argument("--output-dir", default="logs/koala_kry")
    parser.add_argument("--device-count", type=int, default=40)
    parser.add_argument("--samples", type=int, default=250)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    cfg = KoalaKryConfig(output_dir=args.output_dir, device_count=args.device_count, samples=args.samples)
    records = generate_records(cfg, seed=args.seed)
    summary = write_records(records, cfg.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
