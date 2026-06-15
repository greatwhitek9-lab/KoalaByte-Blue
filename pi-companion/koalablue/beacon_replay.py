from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


@dataclass
class ReplayConfig:
    """Local BLE metadata replay configuration.

    Beacon Record & Replay Simulator replays previously captured advertisement
    metadata into local files/stdout for UI, parser, report, and XP testing.
    It does not transmit RF and does not interact with BLE devices.
    """

    input_path: str
    output_dir: str = "logs/beacon_replay"
    speed: float = 10.0
    max_records: Optional[int] = None
    preserve_timing: bool = True
    xp_reward: int = 5


@dataclass
class ReplayRecord:
    replay_timestamp: float
    original_timestamp: Optional[float]
    address: str
    name: str
    rssi: Optional[int]
    source_file: str
    replay_source: str = "beacon_record_replay_simulator"
    rf_transmission: bool = False
    note: str = "local metadata replay only; no BLE transmission"


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _pick(record: Dict[str, Any], keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return str(value)
    return default


def normalize_record(raw: Dict[str, Any], source_file: str) -> ReplayRecord:
    timestamp = _safe_float(_pick(raw, ["timestamp", "time", "seen_at", "first_seen", "last_seen"], ""))
    address = _pick(raw, ["address", "mac", "bdaddr", "device_address", "addr"], "unknown")
    name = _pick(raw, ["name", "local_name", "device_name", "ssid"], "")
    rssi = _safe_int(_pick(raw, ["rssi", "signal", "signal_dbm", "best_rssi"], ""))
    return ReplayRecord(
        replay_timestamp=time.time(),
        original_timestamp=timestamp,
        address=address,
        name=name,
        rssi=rssi,
        source_file=source_file,
    )


def load_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_json(path: Path) -> Iterator[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
    elif isinstance(data, dict):
        if isinstance(data.get("records"), list):
            for item in data["records"]:
                if isinstance(item, dict):
                    yield item
        else:
            yield data


def load_csv(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield dict(row)


def load_records(input_path: str | Path) -> List[ReplayRecord]:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".jsonl":
        raw_iter = load_jsonl(path)
    elif path.suffix.lower() == ".json":
        raw_iter = load_json(path)
    elif path.suffix.lower() == ".csv":
        raw_iter = load_csv(path)
    else:
        raise ValueError(f"Unsupported replay input format: {path.suffix}. Use .jsonl, .json, or .csv")
    return [normalize_record(raw, str(path)) for raw in raw_iter]


def replay_records(records: List[ReplayRecord], config: ReplayConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    replay_path = out / f"beacon_replay_{stamp}.jsonl"
    summary_path = out / f"beacon_replay_{stamp}_summary.json"

    selected = records[: config.max_records] if config.max_records else records
    last_original: Optional[float] = None
    written = 0

    with replay_path.open("w", encoding="utf-8") as fh:
        for rec in selected:
            if config.preserve_timing and last_original is not None and rec.original_timestamp is not None:
                delay = max(0.0, (rec.original_timestamp - last_original) / max(config.speed, 0.1))
                time.sleep(min(delay, 2.0))
            last_original = rec.original_timestamp if rec.original_timestamp is not None else last_original
            rec.replay_timestamp = time.time()
            payload = asdict(rec)
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
            print(json.dumps(payload, sort_keys=True), flush=True)
            written += 1

    summary = {
        "action": "Beacon Record & Replay Simulator",
        "mode": "local_metadata_replay",
        "input_path": config.input_path,
        "output_path": str(replay_path),
        "summary_path": str(summary_path),
        "records_loaded": len(records),
        "records_replayed": written,
        "speed": config.speed,
        "rf_transmission": False,
        "xp_reward": config.xp_reward,
        "safety_scope": "local replay of previously captured metadata only",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def run_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Beacon Record & Replay Simulator")
    parser.add_argument("--input", required=True, help="Input .jsonl, .json, or .csv capture metadata file")
    parser.add_argument("--output-dir", default="logs/beacon_replay")
    parser.add_argument("--speed", type=float, default=10.0, help="Timing replay speed multiplier")
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--no-timing", action="store_true", help="Replay immediately without timing delays")
    args = parser.parse_args()

    config = ReplayConfig(
        input_path=args.input,
        output_dir=args.output_dir,
        speed=args.speed,
        max_records=args.max_records,
        preserve_timing=not args.no_timing,
    )
    records = load_records(config.input_path)
    summary = replay_records(records, config)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
