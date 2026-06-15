from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class KoalaKryConfig:
    """Offline captured BLE metadata replay simulator.

    Koala Kry replays metadata captured by Koala Kapture into local output files
    and console events. It does not transmit BLE advertisements, RF packets, or
    radio noise. It is intended for UI, parser, report, eucalyptus, Urban
    Poaching, and XP-system testing.
    """

    input_path: Optional[str] = None
    input_dir: str = "/blecaptures/koala_kapture"
    output_dir: str = "logs/koala_kry_replay"
    speed: float = 1.0
    loop: bool = False
    max_records: Optional[int] = None
    xp_reward: int = 5


@dataclass
class ReplayEvent:
    replay_timestamp: float
    source_timestamp: Optional[float]
    address: str
    name: str
    rssi: Optional[int]
    record_type: str = "koala_kry_replay_event"
    source: str = "Koala Kry"
    replay_mode: str = "offline_metadata_replay"
    rf_transmission: bool = False
    original_record: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KoalaKryReplayResult:
    action: str
    input_path: str
    started_at: float
    ended_at: float
    replayed_records: int
    output_jsonl_path: str
    summary_path: str
    xp_reward: int


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _load_json(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [dict(item) for item in payload["records"]]
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(f"Unsupported JSON replay format: {path}")


def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def load_capture_records(path: Path) -> List[Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return _load_jsonl(path)
    if suffix == ".json":
        return _load_json(path)
    if suffix == ".csv":
        return _load_csv(path)
    raise ValueError(f"Unsupported replay input type: {path.suffix}")


def find_latest_capture(input_dir: str | Path) -> Path:
    root = Path(input_dir)
    candidates = sorted(
        list(root.glob("*.jsonl")) + list(root.glob("*.json")) + list(root.glob("*.csv")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No capture files found in {root}")
    return candidates[0]


def _timestamp(record: Dict[str, Any]) -> Optional[float]:
    value = record.get("timestamp")
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _rssi(record: Dict[str, Any]) -> Optional[int]:
    value = record.get("rssi")
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


class KoalaKryReplay:
    def __init__(self, config: Optional[KoalaKryConfig] = None) -> None:
        self.config = config or KoalaKryConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def replay(self) -> KoalaKryReplayResult:
        input_path = Path(self.config.input_path) if self.config.input_path else find_latest_capture(self.config.input_dir)
        records = load_capture_records(input_path)
        records = sorted(records, key=lambda rec: _timestamp(rec) or 0.0)
        if self.config.max_records is not None:
            records = records[: self.config.max_records]

        started = time.time()
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(started))
        output_jsonl = self.output_dir / f"koala_kry_replay_{stamp}.jsonl"
        summary_path = self.output_dir / f"koala_kry_replay_{stamp}_summary.json"

        replayed = 0
        previous_ts: Optional[float] = None
        with output_jsonl.open("w", encoding="utf-8") as fh:
            while True:
                for record in records:
                    source_ts = _timestamp(record)
                    if previous_ts is not None and source_ts is not None and self.config.speed > 0:
                        delay = max(0.0, (source_ts - previous_ts) / self.config.speed)
                        if delay > 0:
                            time.sleep(min(delay, 5.0))
                    previous_ts = source_ts if source_ts is not None else previous_ts
                    event = ReplayEvent(
                        replay_timestamp=time.time(),
                        source_timestamp=source_ts,
                        address=str(record.get("address", "")),
                        name=str(record.get("name", record.get("local_name", "")) or ""),
                        rssi=_rssi(record),
                        original_record=record,
                    )
                    fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")
                    replayed += 1
                if not self.config.loop:
                    break

        ended = time.time()
        summary = {
            "action": "Koala Kry",
            "mode": "captured_metadata_replay",
            "rf_transmission": False,
            "input_path": str(input_path),
            "started_at": started,
            "ended_at": ended,
            "replayed_records": replayed,
            "output_jsonl_path": str(output_jsonl),
            "xp_reward": self.config.xp_reward,
            "safety_scope": "offline metadata replay only",
        }
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return KoalaKryReplayResult(
            action="Koala Kry",
            input_path=str(input_path),
            started_at=started,
            ended_at=ended,
            replayed_records=replayed,
            output_jsonl_path=str(output_jsonl),
            summary_path=str(summary_path),
            xp_reward=self.config.xp_reward,
        )


def run_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Koala Kry offline captured BLE metadata replay")
    parser.add_argument("--input", dest="input_path", default=None, help="Capture file to replay: jsonl, json, or csv")
    parser.add_argument("--input-dir", default="/blecaptures/koala_kapture", help="Directory used when --input is omitted")
    parser.add_argument("--output-dir", default="logs/koala_kry_replay")
    parser.add_argument("--speed", type=float, default=1.0, help="Replay speed multiplier")
    parser.add_argument("--max-records", type=int, default=None)
    args = parser.parse_args()

    config = KoalaKryConfig(
        input_path=args.input_path,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        speed=args.speed,
        max_records=args.max_records,
    )
    result = KoalaKryReplay(config).replay()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
