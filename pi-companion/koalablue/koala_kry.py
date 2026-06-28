from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_PROMPT_PATH = Path("logs/koala_kry_replay/prompt.json")
DEFAULT_INPUT_DIR = "/blecaptures/koala_kapture"
DEFAULT_OUTPUT_DIR = "logs/koala_kry_replay"


@dataclass
class KoalaKryConfig:
    """Offline captured BLE metadata replay simulator.

    Koala Kry replays metadata captured by Koala Kapture into local output files
    and console events. It does not transmit BLE advertisements, RF packets, or
    radio noise. It is intended for UI, parser, report, eucalyptus, Urban
    Poaching, and XP-system testing. The RF review action writes bench-isolation
    and authorization notes only.
    """

    input_path: Optional[str] = None
    input_dir: str = DEFAULT_INPUT_DIR
    output_dir: str = DEFAULT_OUTPUT_DIR
    speed: float = 1.0
    loop: bool = False
    max_records: Optional[int] = None
    xp_reward: int = 5
    request_rf_transmit: bool = False
    lab_setting_ack: bool = False
    owned_device_ack: bool = False
    write_transmit_review: bool = False


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
    rf_transmit_requested: bool = False
    rf_transmit_status: str = "not_requested"
    transmit_review_path: Optional[str] = None


@dataclass
class KoalaKryTransmitReview:
    action: str
    status: str
    requested_at: float
    input_path: str
    records_reviewed: int
    rf_transmission: bool
    policy: str
    lab_setting_ack: bool
    owned_device_ack: bool
    allowed_next_steps: List[str]
    blocked_actions: List[str]
    required_lab_controls: List[str]
    review_notes: List[str]


def _truthy_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, ""))
    except ValueError:
        return default


def _env_int_optional(name: str) -> Optional[int]:
    value = os.getenv(name, "")
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def default_prompt_state() -> dict[str, Any]:
    return {
        "input_path": os.getenv("KOALA_KRY_INPUT_PATH") or os.getenv("KOALA_KRY_INPUT") or "",
        "input_dir": os.getenv("KOALA_KRY_INPUT_DIR") or DEFAULT_INPUT_DIR,
        "output_dir": os.getenv("KOALA_KRY_OUTPUT_DIR") or DEFAULT_OUTPUT_DIR,
        "speed": _env_float("KOALA_KRY_SPEED", 1.0),
        "loop": _truthy_env("KOALA_KRY_LOOP", False),
        "max_records": _env_int_optional("KOALA_KRY_MAX_RECORDS"),
        "write_transmit_review": _truthy_env("KOALA_KRY_WRITE_REVIEW", False),
        "lab_setting_ack": _truthy_env("KOALA_KRY_LAB_SETTING_ACK", False),
        "owned_device_ack": _truthy_env("KOALA_KRY_OWNED_DEVICE_ACK", False),
        "source": "environment" if os.getenv("KOALA_KRY_INPUT_PATH") or os.getenv("KOALA_KRY_INPUT") else "default",
    }


def load_prompt_state(path: str | Path = DEFAULT_PROMPT_PATH) -> dict[str, Any]:
    state = default_prompt_state()
    target = Path(path)
    if target.exists():
        try:
            saved = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                state.update(saved)
                state["source"] = "menu_saved"
        except Exception as exc:
            state["load_error"] = str(exc)
    for env_name, state_key in [("KOALA_KRY_INPUT_PATH", "input_path"), ("KOALA_KRY_INPUT", "input_path"), ("KOALA_KRY_INPUT_DIR", "input_dir"), ("KOALA_KRY_OUTPUT_DIR", "output_dir")]:
        if os.getenv(env_name):
            state[state_key] = os.getenv(env_name)
            state["source"] = "environment"
    if os.getenv("KOALA_KRY_SPEED"):
        state["speed"] = _env_float("KOALA_KRY_SPEED", float(state.get("speed", 1.0) or 1.0))
    if os.getenv("KOALA_KRY_MAX_RECORDS"):
        state["max_records"] = _env_int_optional("KOALA_KRY_MAX_RECORDS")
    for env_name, state_key in [("KOALA_KRY_WRITE_REVIEW", "write_transmit_review"), ("KOALA_KRY_LAB_SETTING_ACK", "lab_setting_ack"), ("KOALA_KRY_OWNED_DEVICE_ACK", "owned_device_ack")]:
        if os.getenv(env_name) is not None:
            state[state_key] = _truthy_env(env_name, bool(state.get(state_key, False)))
    return state


def save_prompt_state(state: dict[str, Any], path: str | Path = DEFAULT_PROMPT_PATH) -> dict[str, Any]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    max_records = state.get("max_records") if isinstance(state.get("max_records"), int) and int(state.get("max_records")) > 0 else None
    clean = {
        "input_path": str(state.get("input_path", "")),
        "input_dir": str(state.get("input_dir", DEFAULT_INPUT_DIR) or DEFAULT_INPUT_DIR),
        "output_dir": str(state.get("output_dir", DEFAULT_OUTPUT_DIR) or DEFAULT_OUTPUT_DIR),
        "speed": float(state.get("speed", 1.0) or 0.0),
        "loop": bool(state.get("loop", False)),
        "max_records": max_records,
        "write_transmit_review": bool(state.get("write_transmit_review", False)),
        "lab_setting_ack": bool(state.get("lab_setting_ack", False)),
        "owned_device_ack": bool(state.get("owned_device_ack", False)),
        "updated_at": time.time(),
        "scope": "menu-managed Koala Kry offline replay prompt; no RF transmission settings are stored",
    }
    target.write_text(json.dumps(clean, indent=2, sort_keys=True), encoding="utf-8")
    return {"saved": True, "path": str(target), "koala_kry_prompt": clean}


def prompt_status(log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    state = load_prompt_state()
    payload = {"action": "koala_kry_prompt_status", "status": "KOALA_KRY_PROMPT_READY", "prompt": state, "prompt_path": str(DEFAULT_PROMPT_PATH)}
    return _write_result("prompt_status", payload, log_dir)


def set_latest_capture(log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    state = load_prompt_state()
    try:
        latest = find_latest_capture(str(state.get("input_dir") or DEFAULT_INPUT_DIR))
        state["input_path"] = str(latest)
        saved = save_prompt_state(state)
        payload = {"action": "koala_kry_set_latest_capture", "status": "KOALA_KRY_LATEST_CAPTURE_SET", "latest_capture": str(latest), **saved}
    except Exception as exc:
        payload = {"action": "koala_kry_set_latest_capture", "status": "KOALA_KRY_NO_CAPTURE_FOUND", "error": str(exc), "prompt": state}
    return _write_result("set_latest_capture", payload, log_dir)


def set_speed_preset(preset: str, log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    speeds = {"live": 1.0, "fast": 5.0, "instant": 0.0}
    state = load_prompt_state()
    state["speed"] = speeds.get(preset, 1.0)
    saved = save_prompt_state(state)
    payload = {"action": "koala_kry_set_speed", "status": "KOALA_KRY_SPEED_SET", "preset": preset, **saved}
    return _write_result("set_speed", payload, log_dir)


def set_record_limit(limit: Optional[int], log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    state = load_prompt_state()
    state["max_records"] = limit if isinstance(limit, int) and limit > 0 else None
    saved = save_prompt_state(state)
    payload = {"action": "koala_kry_set_record_limit", "status": "KOALA_KRY_RECORD_LIMIT_SET", "limit": state["max_records"], **saved}
    return _write_result("set_record_limit", payload, log_dir)


def set_rf_review(enabled: bool, log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    state = load_prompt_state()
    state["write_transmit_review"] = bool(enabled)
    saved = save_prompt_state(state)
    payload = {"action": "koala_kry_set_rf_review", "status": "KOALA_KRY_RF_REVIEW_ON" if enabled else "KOALA_KRY_RF_REVIEW_OFF", **saved}
    return _write_result("set_rf_review", payload, log_dir)


def set_lab_ack(enabled: bool, log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    state = load_prompt_state()
    state["lab_setting_ack"] = bool(enabled)
    saved = save_prompt_state(state)
    payload = {"action": "koala_kry_set_lab_ack", "status": "KOALA_KRY_LAB_ACK_ON" if enabled else "KOALA_KRY_LAB_ACK_OFF", **saved}
    return _write_result("set_lab_ack", payload, log_dir)


def set_owned_ack(enabled: bool, log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    state = load_prompt_state()
    state["owned_device_ack"] = bool(enabled)
    saved = save_prompt_state(state)
    payload = {"action": "koala_kry_set_owned_ack", "status": "KOALA_KRY_OWNED_ACK_ON" if enabled else "KOALA_KRY_OWNED_ACK_OFF", **saved}
    return _write_result("set_owned_ack", payload, log_dir)


def clear_prompt(log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    saved = save_prompt_state(default_prompt_state())
    payload = {"action": "koala_kry_clear_prompt", "status": "KOALA_KRY_PROMPT_CLEARED", **saved}
    return _write_result("clear_prompt", payload, log_dir)


def config_from_prompt(*, review_only: bool = False) -> KoalaKryConfig:
    state = load_prompt_state()
    input_path = str(state.get("input_path", "")) or None
    max_records = state.get("max_records") if isinstance(state.get("max_records"), int) else None
    return KoalaKryConfig(
        input_path=input_path,
        input_dir=str(state.get("input_dir", DEFAULT_INPUT_DIR) or DEFAULT_INPUT_DIR),
        output_dir=str(state.get("output_dir", DEFAULT_OUTPUT_DIR) or DEFAULT_OUTPUT_DIR),
        speed=float(state.get("speed", 1.0) or 0.0),
        loop=bool(state.get("loop", False)),
        max_records=max_records,
        lab_setting_ack=bool(state.get("lab_setting_ack", False)),
        owned_device_ack=bool(state.get("owned_device_ack", False)),
        write_transmit_review=bool(state.get("write_transmit_review", False)) or review_only,
        request_rf_transmit=False,
    )


def run_from_prompt(*, review_only: bool = False, log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    try:
        result = KoalaKryReplay(config_from_prompt(review_only=review_only)).replay()
        return _write_result("run_from_prompt", {"status": "KOALA_KRY_REPLAY_COMPLETE", "review_only": review_only, "result": asdict(result), "prompt": load_prompt_state()}, log_dir)
    except Exception as exc:
        return _write_result("run_from_prompt_failed", {"status": "KOALA_KRY_REPLAY_BLOCKED", "review_only": review_only, "error": str(exc), "prompt": load_prompt_state(), "next_menu_step": "Choose Use Latest Capture or run Koala Kapture first."}, log_dir)


def _write_result(name: str, payload: dict[str, Any], log_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = Path(log_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"koala_kry_{name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["artifact_path"] = str(path)
    return payload


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
    candidates = sorted(list(root.glob("*.jsonl")) + list(root.glob("*.json")) + list(root.glob("*.csv")), key=lambda p: p.stat().st_mtime, reverse=True)
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
        transmit_review_path: Optional[Path] = None
        rf_transmit_status = "not_requested"

        if self.config.request_rf_transmit or self.config.write_transmit_review:
            transmit_review_path = self._write_transmit_review(input_path=input_path, records=records, requested_at=started, stamp=stamp)
            rf_transmit_status = "rf_bench_review_written_no_rf_sent"

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
                    event = ReplayEvent(replay_timestamp=time.time(), source_timestamp=source_ts, address=str(record.get("address", "")), name=str(record.get("name", record.get("local_name", "")) or ""), rssi=_rssi(record), original_record=record)
                    fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")
                    replayed += 1
                if not self.config.loop:
                    break

        ended = time.time()
        summary = {"action": "Koala Kry", "mode": "captured_metadata_replay", "rf_transmission": False, "rf_transmit_requested": self.config.request_rf_transmit, "rf_transmit_status": rf_transmit_status, "transmit_review_path": str(transmit_review_path) if transmit_review_path else None, "input_path": str(input_path), "started_at": started, "ended_at": ended, "replayed_records": replayed, "output_jsonl_path": str(output_jsonl), "xp_reward": self.config.xp_reward, "safety_scope": "offline metadata replay and RF bench review only; over-the-air captured-signal replay is not implemented"}
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return KoalaKryReplayResult("Koala Kry", str(input_path), started, ended, replayed, str(output_jsonl), str(summary_path), self.config.xp_reward, self.config.request_rf_transmit, rf_transmit_status, str(transmit_review_path) if transmit_review_path else None)

    def _write_transmit_review(self, *, input_path: Path, records: List[Dict[str, Any]], requested_at: float, stamp: str) -> Path:
        review = KoalaKryTransmitReview(
            action="Koala Kry RF bench review",
            status="rf_bench_review_written_no_rf_sent",
            requested_at=requested_at,
            input_path=str(input_path),
            records_reviewed=len(records),
            rf_transmission=False,
            policy="Koala Kry writes an RF bench isolation and authorization review only. It does not transmit RF, replay captured signals, rebroadcast identifiers, or generate radio noise.",
            lab_setting_ack=self.config.lab_setting_ack,
            owned_device_ack=self.config.owned_device_ack,
            allowed_next_steps=["Use Koala Kry offline replay for UI, parser, report, XP, and workflow testing.", "Document RF bench setup, shielding, attenuation, dummy-load use, frequency range, duration, and monitoring plan before any separate test-equipment work.", "Use certified RF test equipment, vendor SDK examples, or a shielded bench fixture only within a legally compliant isolated test setup.", "Create fresh, clearly named synthetic lab payloads instead of replaying captured signals or identifiers.", "Keep WiGLE/upload and BLE observation features passive unless credentials and location are intentionally configured."],
            blocked_actions=["Over-the-air replay of captured Bluetooth/RF signals.", "Rebroadcasting captured device identifiers or payloads.", "Any transmit behavior intended to interfere with, jam, degrade, impersonate, disrupt, or confuse nearby devices.", "Any RF operation outside a documented isolated bench setup."],
            required_lab_controls=["Written scope for the lab session and devices under test.", "Shielded enclosure, dummy load, or equivalent containment appropriate for the equipment being used outside Koala Kry.", "Power, frequency, duration, and antenna/attenuator settings documented before testing.", "Spectrum or channel monitoring plan documented before testing.", "Stop condition documented before testing."],
            review_notes=["This artifact is a preflight review and audit trail, not an RF transmitter.", "Captured metadata remains local and is not converted into an over-the-air signal by Koala Kry.", "Use separate compliant RF lab equipment for any lawful signal-generation work."],
        )
        path = self.output_dir / f"koala_kry_rf_bench_review_{stamp}.json"
        path.write_text(json.dumps(asdict(review), indent=2, sort_keys=True), encoding="utf-8")
        return path


def run_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Koala Kry offline captured BLE metadata replay and RF bench review")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("prompt-status")
    sub.add_parser("use-latest-capture")
    sub.add_parser("speed-live")
    sub.add_parser("speed-fast")
    sub.add_parser("speed-instant")
    sub.add_parser("limit-50")
    sub.add_parser("limit-200")
    sub.add_parser("limit-all")
    sub.add_parser("rf-review-on")
    sub.add_parser("rf-review-off")
    sub.add_parser("lab-ack-on")
    sub.add_parser("owned-ack-on")
    sub.add_parser("clear-prompt")
    sub.add_parser("run-prompt")
    sub.add_parser("run-review")
    parser.add_argument("--input", dest="input_path", default=None, help="Capture file to replay: jsonl, json, or csv")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help="Directory used when --input is omitted")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--speed", type=float, default=1.0, help="Replay speed multiplier")
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--request-rf-transmit", action="store_true", help="Write an RF bench review manifest; Koala Kry does not send RF")
    parser.add_argument("--lab-setting", action="store_true", help="Acknowledge this is an owned/authorized lab setting for the review manifest")
    parser.add_argument("--owned-device", action="store_true", help="Acknowledge reviewed captures are from owned/scope-approved devices")
    parser.add_argument("--write-transmit-review", action="store_true", help="Write an RF bench review manifest without requesting RF transmit")
    args = parser.parse_args()

    if args.command == "prompt-status":
        print(json.dumps(prompt_status(), indent=2, sort_keys=True))
        return 0
    if args.command == "use-latest-capture":
        print(json.dumps(set_latest_capture(), indent=2, sort_keys=True))
        return 0
    if args.command == "speed-live":
        print(json.dumps(set_speed_preset("live"), indent=2, sort_keys=True))
        return 0
    if args.command == "speed-fast":
        print(json.dumps(set_speed_preset("fast"), indent=2, sort_keys=True))
        return 0
    if args.command == "speed-instant":
        print(json.dumps(set_speed_preset("instant"), indent=2, sort_keys=True))
        return 0
    if args.command == "limit-50":
        print(json.dumps(set_record_limit(50), indent=2, sort_keys=True))
        return 0
    if args.command == "limit-200":
        print(json.dumps(set_record_limit(200), indent=2, sort_keys=True))
        return 0
    if args.command == "limit-all":
        print(json.dumps(set_record_limit(None), indent=2, sort_keys=True))
        return 0
    if args.command == "rf-review-on":
        print(json.dumps(set_rf_review(True), indent=2, sort_keys=True))
        return 0
    if args.command == "rf-review-off":
        print(json.dumps(set_rf_review(False), indent=2, sort_keys=True))
        return 0
    if args.command == "lab-ack-on":
        print(json.dumps(set_lab_ack(True), indent=2, sort_keys=True))
        return 0
    if args.command == "owned-ack-on":
        print(json.dumps(set_owned_ack(True), indent=2, sort_keys=True))
        return 0
    if args.command == "clear-prompt":
        print(json.dumps(clear_prompt(), indent=2, sort_keys=True))
        return 0
    if args.command == "run-prompt":
        print(json.dumps(run_from_prompt(), indent=2, sort_keys=True))
        return 0
    if args.command == "run-review":
        print(json.dumps(run_from_prompt(review_only=True), indent=2, sort_keys=True))
        return 0

    config = KoalaKryConfig(input_path=args.input_path, input_dir=args.input_dir, output_dir=args.output_dir, speed=args.speed, max_records=args.max_records, request_rf_transmit=args.request_rf_transmit, lab_setting_ack=args.lab_setting, owned_device_ack=args.owned_device, write_transmit_review=args.write_transmit_review)
    result = KoalaKryReplay(config).replay()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    if args.request_rf_transmit:
        print("Koala Kry wrote an RF bench review manifest. No RF was sent by Koala Kry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
