from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


ACTION_ID = "thats_not_a_knife"
ACTION_NAME = "that’s not a knife"
KILLERKOALA_ALERT = "Crikey’ mate. i blocked a SKID!"
XP_REWARD = 20
DEFAULT_OUTPUT_DIR = Path("logs/thats_not_a_knife")
DEFAULT_XP_PATH = Path("logs/killerkoala/xp_state.json")
DEFAULT_STATE_PATH = Path("logs/thats_not_a_knife/guard_state.json")
DEFAULT_BLOCK_PATH = Path("logs/thats_not_a_knife/ble_workflow_block.json")


@dataclass
class GuardSignal:
    source: str
    reason: str
    weight: int = 1


@dataclass
class GuardResult:
    action_id: str
    action_name: str
    status: str
    always_on: bool
    local_guard_enabled: bool
    defensive_block_successful: bool
    companion_alert: str
    started_at: float
    ended_at: float
    pressure_score: int
    xp_reward: int = 0
    xp_before: int = 0
    xp_after: int = 0
    signals: List[GuardSignal] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    safety: Dict[str, object] = field(default_factory=dict)
    details: Dict[str, object] = field(default_factory=dict)


def _rank_for_xp(xp: int) -> str:
    if xp >= 250:
        return "Legend"
    if xp >= 75:
        return "Hacker"
    return "Noob"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_xp(path: Path) -> dict:
    if not path.exists():
        return {"xp": 0, "rank": _rank_for_xp(0), "successful_modules": 0, "failed_modules": 0, "last_module": "", "updated_at": time.time()}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        xp = int(data.get("xp", 0))
        return {
            "xp": xp,
            "rank": _rank_for_xp(xp),
            "successful_modules": int(data.get("successful_modules", 0)),
            "failed_modules": int(data.get("failed_modules", 0)),
            "last_module": str(data.get("last_module", "")),
            "updated_at": float(data.get("updated_at", time.time())),
        }
    except Exception:
        return {"xp": 0, "rank": _rank_for_xp(0), "successful_modules": 0, "failed_modules": 0, "last_module": "", "updated_at": time.time()}


def _award_xp(path: Path, reward: int) -> tuple[int, int]:
    state = _load_xp(path)
    before = int(state.get("xp", 0))
    state["xp"] = before + reward
    state["rank"] = _rank_for_xp(int(state["xp"]))
    state["successful_modules"] = int(state.get("successful_modules", 0)) + 1
    state["last_module"] = ACTION_NAME
    state["updated_at"] = time.time()
    _write_json(path, state)
    return before, int(state["xp"])


def _signals_from_metrics(metrics: dict) -> List[GuardSignal]:
    signals: List[GuardSignal] = []
    connection_errors = int(metrics.get("connection_errors", 0) or 0)
    repeated_connects = int(metrics.get("repeated_connects", 0) or 0)
    scan_backlog = int(metrics.get("scan_backlog", 0) or 0)
    adapter_resets = int(metrics.get("adapter_resets", 0) or 0)
    if connection_errors >= 5:
        signals.append(GuardSignal("metrics", "connection error spike", 3))
    if repeated_connects >= 8:
        signals.append(GuardSignal("metrics", "repeated connect pressure", 3))
    if scan_backlog >= 50:
        signals.append(GuardSignal("metrics", "scan backlog spike", 2))
    if adapter_resets >= 2:
        signals.append(GuardSignal("metrics", "adapter reset pattern", 2))
    return signals


def _signals_from_lines(lines: Iterable[str]) -> List[GuardSignal]:
    markers = {
        "connection failed": ("log", "connection failure pattern", 1),
        "connection timeout": ("log", "connection timeout pattern", 1),
        "resource unavailable": ("log", "local adapter resource pressure", 2),
        "too many": ("log", "connection volume pressure", 2),
        "command disallowed": ("log", "controller command pressure", 1),
    }
    signals: List[GuardSignal] = []
    for line in lines:
        lower = line.lower()
        for marker, spec in markers.items():
            if marker in lower:
                signals.append(GuardSignal(spec[0], spec[1], spec[2]))
    return signals


def _write_block_state(block_path: Path, active: bool, pressure_score: int, threshold: int, timestamp: float) -> bool:
    payload = {
        "action_id": ACTION_ID,
        "action_name": ACTION_NAME,
        "block_active": active,
        "blocked_local_workflows": [
            "scan",
            "koala_kapture",
            "koala_bluez_scan",
            "koala_bluez_monitor",
            "urban_poaching",
        ] if active else [],
        "block_scope": "local KoalaByte Blue BLE workflows",
        "pressure_score": pressure_score,
        "threshold": threshold,
        "updated_at": timestamp,
        "operator_note": "Review guard logs before re-enabling local BLE workflows." if active else "Local BLE workflow block is not active.",
    }
    _write_json(block_path, payload)
    return block_path.exists()


def run_guard_once(
    metrics: Optional[dict] = None,
    log_lines: Optional[Iterable[str]] = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    state_path: str | Path = DEFAULT_STATE_PATH,
    block_path: str | Path = DEFAULT_BLOCK_PATH,
    xp_path: str | Path = DEFAULT_XP_PATH,
    threshold: int = 5,
    award_xp: bool = True,
) -> GuardResult:
    started = time.time()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    state_path = Path(state_path)
    block_path = Path(block_path)
    signals = _signals_from_metrics(metrics or {}) + _signals_from_lines(log_lines or [])
    pressure_score = sum(signal.weight for signal in signals)
    local_guard_enabled = pressure_score >= threshold
    defensive_block_successful = False
    block_error: Optional[str] = None

    ended = time.time()
    summary_path = output_path / f"thats_not_a_knife_{int(started)}.json"
    alert_path = output_path / "killerkoala_alert.txt"
    companion_alert = KILLERKOALA_ALERT if local_guard_enabled else "killerkoala is watching the BLE canopy."

    try:
        defensive_block_successful = _write_block_state(block_path, local_guard_enabled, pressure_score, threshold, ended) if local_guard_enabled else _write_block_state(block_path, False, pressure_score, threshold, ended)
        if not local_guard_enabled:
            defensive_block_successful = False
        state = {
            "action_id": ACTION_ID,
            "action_name": ACTION_NAME,
            "always_on": True,
            "local_guard_enabled": local_guard_enabled,
            "defensive_block_successful": defensive_block_successful,
            "status": "BLOCKED" if defensive_block_successful else ("BLOCK_FAILED" if local_guard_enabled else "MONITORING"),
            "pressure_score": pressure_score,
            "threshold": threshold,
            "updated_at": ended,
            "companion_alert": companion_alert,
            "recommended_operator_action": "Pause active BLE workflows and review logs before re-enabling local Bluetooth actions." if defensive_block_successful else "Continue monitoring.",
        }
        _write_json(state_path, state)
        alert_path.write_text(companion_alert + "\n", encoding="utf-8")
    except Exception as exc:
        defensive_block_successful = False
        block_error = str(exc)
        companion_alert = "killerkoala saw pressure but could not activate the local block. Check permissions and storage."

    xp_state = _load_xp(Path(xp_path))
    xp_before = int(xp_state.get("xp", 0))
    xp_after = xp_before
    xp_reward = XP_REWARD if defensive_block_successful and award_xp else 0
    if xp_reward:
        xp_before, xp_after = _award_xp(Path(xp_path), xp_reward)

    status = "BLOCKED" if defensive_block_successful else ("BLOCK_FAILED" if local_guard_enabled else "MONITORING")
    result = GuardResult(
        action_id=ACTION_ID,
        action_name=ACTION_NAME,
        status=status,
        always_on=True,
        local_guard_enabled=local_guard_enabled,
        defensive_block_successful=defensive_block_successful,
        companion_alert=companion_alert,
        started_at=started,
        ended_at=ended,
        pressure_score=pressure_score,
        xp_reward=xp_reward,
        xp_before=xp_before,
        xp_after=xp_after,
        signals=signals,
        artifacts={"summary": str(summary_path), "guard_state": str(state_path), "workflow_block": str(block_path), "killerkoala_alert": str(alert_path)},
        safety={
            "authorized_lab_use_only": True,
            "local_guard_state_only": True,
            "over_the_air_response": False,
            "spoofing": False,
            "packet_replay": False,
            "offensive_frames_sent": False,
            "xp_awarded_only_after_defensive_block_success": True,
        },
        details={"threshold": threshold, "signal_count": len(signals), "block_error": block_error},
    )
    _write_json(summary_path, asdict(result))
    return result


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue always-on BLE defense guard: that’s not a knife")
    parser.add_argument("--metrics-json", default=None, help="Optional JSON object with defensive counters")
    parser.add_argument("--log-file", default=None, help="Optional local log file to inspect for defensive pressure markers")
    parser.add_argument("--threshold", type=int, default=5)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--block-path", default=str(DEFAULT_BLOCK_PATH))
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    parser.add_argument("--no-award-xp", action="store_true")
    args = parser.parse_args()

    metrics = json.loads(args.metrics_json) if args.metrics_json else {}
    lines: List[str] = []
    if args.log_file:
        path = Path(args.log_file)
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]

    result = run_guard_once(metrics=metrics, log_lines=lines, output_dir=args.output_dir, state_path=args.state_path, block_path=args.block_path, xp_path=args.xp_path, threshold=args.threshold, award_xp=not args.no_award_xp)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
