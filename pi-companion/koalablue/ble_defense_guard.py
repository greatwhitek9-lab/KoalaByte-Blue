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


def run_guard_once(
    metrics: Optional[dict] = None,
    log_lines: Optional[Iterable[str]] = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    state_path: str | Path = DEFAULT_STATE_PATH,
    xp_path: str | Path = DEFAULT_XP_PATH,
    threshold: int = 5,
    award_xp: bool = True,
) -> GuardResult:
    started = time.time()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    signals = _signals_from_metrics(metrics or {}) + _signals_from_lines(log_lines or [])
    pressure_score = sum(signal.weight for signal in signals)
    local_guard_enabled = pressure_score >= threshold
    status = "GUARD_ACTIVE" if local_guard_enabled else "MONITORING"

    xp_before = int(_load_xp(Path(xp_path)).get("xp", 0))
    xp_after = xp_before
    xp_reward = XP_REWARD if local_guard_enabled else 0
    if local_guard_enabled and award_xp:
        xp_before, xp_after = _award_xp(Path(xp_path), xp_reward)

    ended = time.time()
    summary_path = output_path / f"thats_not_a_knife_{int(started)}.json"
    alert_path = output_path / "killerkoala_alert.txt"
    state = {
        "action_id": ACTION_ID,
        "action_name": ACTION_NAME,
        "always_on": True,
        "local_guard_enabled": local_guard_enabled,
        "status": status,
        "pressure_score": pressure_score,
        "threshold": threshold,
        "updated_at": ended,
        "companion_alert": KILLERKOALA_ALERT if local_guard_enabled else "killerkoala is watching the BLE canopy.",
        "recommended_operator_action": "Pause active BLE workflows and review logs before re-enabling local Bluetooth actions." if local_guard_enabled else "Continue monitoring.",
    }
    _write_json(Path(state_path), state)
    alert_path.write_text(state["companion_alert"] + "\n", encoding="utf-8")

    result = GuardResult(
        action_id=ACTION_ID,
        action_name=ACTION_NAME,
        status=status,
        always_on=True,
        local_guard_enabled=local_guard_enabled,
        companion_alert=state["companion_alert"],
        started_at=started,
        ended_at=ended,
        pressure_score=pressure_score,
        xp_reward=xp_reward,
        xp_before=xp_before,
        xp_after=xp_after,
        signals=signals,
        artifacts={"summary": str(summary_path), "guard_state": str(state_path), "killerkoala_alert": str(alert_path)},
        safety={
            "authorized_lab_use_only": True,
            "local_guard_state_only": True,
            "over_the_air_response": False,
            "spoofing": False,
            "packet_replay": False,
            "offensive_frames_sent": False,
            "xp_awarded_on_guard_activation_only": True,
        },
        details={"threshold": threshold, "signal_count": len(signals)},
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
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    parser.add_argument("--no-award-xp", action="store_true")
    args = parser.parse_args()

    metrics = json.loads(args.metrics_json) if args.metrics_json else {}
    lines: List[str] = []
    if args.log_file:
        path = Path(args.log_file)
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]

    result = run_guard_once(metrics=metrics, log_lines=lines, output_dir=args.output_dir, state_path=args.state_path, xp_path=args.xp_path, threshold=args.threshold, award_xp=not args.no_award_xp)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
