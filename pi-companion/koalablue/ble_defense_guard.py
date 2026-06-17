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
DEFAULT_SETTINGS_PATH = Path("logs/thats_not_a_knife/monitor_settings.json")

MONITOR_REGISTRY: Dict[str, dict] = {
    "dos_pressure": {
        "display_name": "BLE DoS pressure guard",
        "default_enabled": True,
        "threshold": 5,
        "description": "Detects repeated local connection/controller pressure patterns and blocks local BLE workflows.",
    },
    "bluesnarfing": {
        "display_name": "bluesnarfing / blue snarfing guard",
        "default_enabled": True,
        "threshold": 4,
        "description": "Detects suspicious local OBEX/PBAP/file-pull style access patterns and blocks local BLE workflows.",
    },
    "bluebugging": {
        "display_name": "bluebugging guard",
        "default_enabled": True,
        "threshold": 4,
        "description": "Detects suspicious local RFCOMM/AT-command/control-channel style patterns and blocks local BLE workflows.",
    },
    "mitm_guard": {
        "display_name": "man-in-the-middle risk guard",
        "default_enabled": True,
        "threshold": 4,
        "description": "Detects suspicious pairing, authorization, key-change, and authentication-failure patterns and blocks local BLE workflows.",
    },
}

MONITOR_ALIASES = {
    "dos": "dos_pressure",
    "ble_dos": "dos_pressure",
    "bluesnarf": "bluesnarfing",
    "blue_snarfing": "bluesnarfing",
    "blue-snarfing": "bluesnarfing",
    "bluesnarffing": "bluesnarfing",
    "mitm": "mitm_guard",
    "man_in_the_middle": "mitm_guard",
    "man-in-the-middle": "mitm_guard",
}


@dataclass
class GuardSignal:
    source: str
    reason: str
    weight: int = 1
    monitor_id: str = "dos_pressure"


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
    active_monitors: List[str] = field(default_factory=list)
    disabled_monitors: List[str] = field(default_factory=list)
    monitor_scores: Dict[str, int] = field(default_factory=dict)
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


def _normalize_monitor_id(monitor_id: str) -> str:
    key = monitor_id.strip().lower().replace(" ", "_")
    key = MONITOR_ALIASES.get(key, key)
    if key not in MONITOR_REGISTRY:
        raise ValueError(f"Unknown monitor '{monitor_id}'. Valid monitors: {', '.join(MONITOR_REGISTRY)}")
    return key


def default_monitor_settings() -> dict:
    return {
        "version": 1,
        "updated_at": time.time(),
        "monitors": {
            monitor_id: {
                "enabled": bool(spec["default_enabled"]),
                "threshold": int(spec["threshold"]),
                "display_name": str(spec["display_name"]),
                "description": str(spec["description"]),
            }
            for monitor_id, spec in MONITOR_REGISTRY.items()
        },
    }


def load_monitor_settings(path: str | Path = DEFAULT_SETTINGS_PATH) -> dict:
    settings_path = Path(path)
    settings = default_monitor_settings()
    if settings_path.exists():
        try:
            loaded = json.loads(settings_path.read_text(encoding="utf-8"))
            loaded_monitors = loaded.get("monitors", {}) if isinstance(loaded, dict) else {}
            for monitor_id, spec in settings["monitors"].items():
                existing = loaded_monitors.get(monitor_id, {}) if isinstance(loaded_monitors, dict) else {}
                if isinstance(existing, dict):
                    spec["enabled"] = bool(existing.get("enabled", spec["enabled"]))
                    spec["threshold"] = int(existing.get("threshold", spec["threshold"]))
            settings["updated_at"] = float(loaded.get("updated_at", settings["updated_at"])) if isinstance(loaded, dict) else settings["updated_at"]
        except Exception:
            pass
    _write_json(settings_path, settings)
    return settings


def set_monitor_enabled(monitor_id: str, enabled: bool, path: str | Path = DEFAULT_SETTINGS_PATH) -> dict:
    resolved = _normalize_monitor_id(monitor_id)
    settings = load_monitor_settings(path)
    settings["monitors"][resolved]["enabled"] = bool(enabled)
    settings["updated_at"] = time.time()
    _write_json(Path(path), settings)
    return settings


def set_monitor_threshold(monitor_id: str, threshold: int, path: str | Path = DEFAULT_SETTINGS_PATH) -> dict:
    resolved = _normalize_monitor_id(monitor_id)
    settings = load_monitor_settings(path)
    settings["monitors"][resolved]["threshold"] = max(1, int(threshold))
    settings["updated_at"] = time.time()
    _write_json(Path(path), settings)
    return settings


def _enabled_monitors(settings: dict) -> Dict[str, dict]:
    monitors = settings.get("monitors", {})
    return {monitor_id: spec for monitor_id, spec in monitors.items() if monitor_id in MONITOR_REGISTRY and bool(spec.get("enabled", True))}


def _disabled_monitor_ids(settings: dict) -> List[str]:
    monitors = settings.get("monitors", {})
    return [monitor_id for monitor_id, spec in monitors.items() if monitor_id in MONITOR_REGISTRY and not bool(spec.get("enabled", True))]


def _signals_from_metrics(metrics: dict) -> List[GuardSignal]:
    signals: List[GuardSignal] = []
    metric_rules = {
        "dos_pressure": [
            ("connection_errors", 5, "connection error spike", 3),
            ("repeated_connects", 8, "repeated connect pressure", 3),
            ("scan_backlog", 50, "scan backlog spike", 2),
            ("adapter_resets", 2, "adapter reset pattern", 2),
        ],
        "bluesnarfing": [
            ("obex_requests", 3, "unexpected object exchange pressure", 2),
            ("pbap_requests", 2, "unexpected phonebook access pressure", 3),
            ("file_pull_requests", 2, "unexpected file pull pressure", 3),
        ],
        "bluebugging": [
            ("rfcomm_sessions", 4, "unexpected RFCOMM session pressure", 2),
            ("at_command_attempts", 2, "unexpected control-command pressure", 3),
            ("hfp_control_attempts", 2, "unexpected handsfree control pressure", 2),
        ],
        "mitm_guard": [
            ("pairing_prompts", 3, "unexpected pairing prompt pressure", 2),
            ("auth_failures", 3, "authentication failure pattern", 2),
            ("key_changes", 1, "unexpected key-change event", 3),
            ("unknown_pairing_attempts", 1, "unknown pairing attempt", 3),
        ],
    }
    for monitor_id, rules in metric_rules.items():
        for key, limit, reason, weight in rules:
            value = int(metrics.get(key, 0) or 0)
            if value >= limit:
                signals.append(GuardSignal("metrics", reason, weight, monitor_id))
    return signals


def _signals_from_lines(lines: Iterable[str]) -> List[GuardSignal]:
    markers = {
        "dos_pressure": {
            "connection failed": ("log", "connection failure pattern", 1),
            "connection timeout": ("log", "connection timeout pattern", 1),
            "resource unavailable": ("log", "local adapter resource pressure", 2),
            "too many": ("log", "connection volume pressure", 2),
            "command disallowed": ("log", "controller command pressure", 1),
        },
        "bluesnarfing": {
            "obex": ("log", "unexpected object exchange marker", 2),
            "pbap": ("log", "unexpected phonebook access marker", 3),
            "phonebook": ("log", "phonebook access marker", 3),
            "vcard": ("log", "contact-card access marker", 2),
            "file pull": ("log", "file pull marker", 3),
            "object push": ("log", "object profile marker", 1),
            "ftp": ("log", "file transfer profile marker", 2),
        },
        "bluebugging": {
            "rfcomm": ("log", "RFCOMM channel marker", 2),
            "at command": ("log", "control-command marker", 3),
            "handsfree": ("log", "handsfree control marker", 2),
            "headset": ("log", "headset profile control marker", 1),
            "audio gateway": ("log", "audio gateway control marker", 2),
            "call control": ("log", "call control marker", 3),
            "serial profile": ("log", "serial profile marker", 2),
        },
        "mitm_guard": {
            "pairing request": ("log", "pairing request marker", 2),
            "just works": ("log", "weak pairing method marker", 2),
            "numeric comparison": ("log", "pairing confirmation marker", 1),
            "confirm passkey": ("log", "passkey confirmation marker", 2),
            "authentication failed": ("log", "authentication failure marker", 2),
            "authorization request": ("log", "authorization request marker", 2),
            "link key changed": ("log", "link-key change marker", 3),
            "legacy pairing": ("log", "legacy pairing marker", 3),
        },
    }
    signals: List[GuardSignal] = []
    for line in lines:
        lower = line.lower()
        for monitor_id, monitor_markers in markers.items():
            for marker, spec in monitor_markers.items():
                if marker in lower:
                    signals.append(GuardSignal(spec[0], spec[1], spec[2], monitor_id))
    return signals


def _score_by_monitor(signals: Iterable[GuardSignal], enabled: Dict[str, dict]) -> Dict[str, int]:
    scores = {monitor_id: 0 for monitor_id in MONITOR_REGISTRY}
    for signal in signals:
        if signal.monitor_id in enabled:
            scores[signal.monitor_id] += int(signal.weight)
    return scores


def _triggered_monitors(scores: Dict[str, int], enabled: Dict[str, dict]) -> List[str]:
    triggered: List[str] = []
    for monitor_id, spec in enabled.items():
        threshold = int(spec.get("threshold", MONITOR_REGISTRY[monitor_id]["threshold"]))
        if int(scores.get(monitor_id, 0)) >= threshold:
            triggered.append(monitor_id)
    return triggered


def _write_block_state(block_path: Path, active: bool, pressure_score: int, threshold: int, timestamp: float, active_monitors: List[str], monitor_scores: Dict[str, int]) -> bool:
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
            "pairing_prompts",
            "object_profile_access",
            "rfcomm_control_channels",
        ] if active else [],
        "active_monitors": active_monitors,
        "monitor_scores": monitor_scores,
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
    settings_path: str | Path = DEFAULT_SETTINGS_PATH,
    xp_path: str | Path = DEFAULT_XP_PATH,
    threshold: int = 5,
    award_xp: bool = True,
) -> GuardResult:
    started = time.time()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    state_path = Path(state_path)
    block_path = Path(block_path)
    settings_path = Path(settings_path)
    settings = load_monitor_settings(settings_path)
    enabled = _enabled_monitors(settings)
    disabled_monitors = _disabled_monitor_ids(settings)

    all_signals = _signals_from_metrics(metrics or {}) + _signals_from_lines(log_lines or [])
    signals = [signal for signal in all_signals if signal.monitor_id in enabled]
    monitor_scores = _score_by_monitor(signals, enabled)
    active_monitors = _triggered_monitors(monitor_scores, enabled)
    pressure_score = sum(monitor_scores.values())
    local_guard_enabled = bool(active_monitors)
    defensive_block_successful = False
    block_error: Optional[str] = None

    ended = time.time()
    summary_path = output_path / f"thats_not_a_knife_{int(started)}.json"
    alert_path = output_path / "killerkoala_alert.txt"
    companion_alert = KILLERKOALA_ALERT if local_guard_enabled else "killerkoala is watching the BLE canopy."

    try:
        defensive_block_successful = _write_block_state(block_path, local_guard_enabled, pressure_score, threshold, ended, active_monitors, monitor_scores)
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
            "active_monitors": active_monitors,
            "disabled_monitors": disabled_monitors,
            "monitor_scores": monitor_scores,
            "settings_path": str(settings_path),
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
        active_monitors=active_monitors,
        disabled_monitors=disabled_monitors,
        monitor_scores=monitor_scores,
        artifacts={"summary": str(summary_path), "guard_state": str(state_path), "workflow_block": str(block_path), "monitor_settings": str(settings_path), "killerkoala_alert": str(alert_path)},
        safety={
            "authorized_lab_use_only": True,
            "local_guard_state_only": True,
            "over_the_air_response": False,
            "spoofing": False,
            "packet_replay": False,
            "offensive_frames_sent": False,
            "xp_awarded_only_after_defensive_block_success": True,
            "individual_monitor_toggles": True,
        },
        details={"threshold": threshold, "signal_count": len(signals), "block_error": block_error, "known_monitors": list(MONITOR_REGISTRY)},
    )
    _write_json(summary_path, asdict(result))
    return result


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue always-on BLE defense guard suite: that’s not a knife")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "status", "enable", "disable", "threshold", "list"], help="run the guard or manage individual monitors")
    parser.add_argument("monitor", nargs="?", default=None, help="Monitor id or alias for enable/disable/threshold")
    parser.add_argument("value", nargs="?", default=None, help="Threshold value when command=threshold")
    parser.add_argument("--metrics-json", default=None, help="Optional JSON object with defensive counters")
    parser.add_argument("--log-file", default=None, help="Optional local log file to inspect for defensive pressure markers")
    parser.add_argument("--threshold", type=int, default=5)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--block-path", default=str(DEFAULT_BLOCK_PATH))
    parser.add_argument("--settings-path", default=str(DEFAULT_SETTINGS_PATH))
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    parser.add_argument("--no-award-xp", action="store_true")
    args = parser.parse_args()

    if args.command in {"status", "list"}:
        _print_json(load_monitor_settings(args.settings_path))
        return 0
    if args.command == "enable":
        if not args.monitor:
            parser.error("enable requires a monitor id")
        _print_json(set_monitor_enabled(args.monitor, True, args.settings_path))
        return 0
    if args.command == "disable":
        if not args.monitor:
            parser.error("disable requires a monitor id")
        _print_json(set_monitor_enabled(args.monitor, False, args.settings_path))
        return 0
    if args.command == "threshold":
        if not args.monitor or args.value is None:
            parser.error("threshold requires a monitor id and integer value")
        _print_json(set_monitor_threshold(args.monitor, int(args.value), args.settings_path))
        return 0

    metrics = json.loads(args.metrics_json) if args.metrics_json else {}
    lines: List[str] = []
    if args.log_file:
        path = Path(args.log_file)
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]

    result = run_guard_once(metrics=metrics, log_lines=lines, output_dir=args.output_dir, state_path=args.state_path, block_path=args.block_path, settings_path=args.settings_path, xp_path=args.xp_path, threshold=args.threshold, award_xp=not args.no_award_xp)
    _print_json(asdict(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
