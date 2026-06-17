#!/usr/bin/env python3
"""Continuously run the KoalaByte Blue local BLE defense guard."""

from __future__ import annotations

import argparse
import glob
import json
import time
from pathlib import Path
from typing import Iterable, List

from koalablue.ble_defense_guard import DEFAULT_OUTPUT_DIR, DEFAULT_STATE_PATH, DEFAULT_XP_PATH, run_guard_once


DEFAULT_LOG_GLOBS = [
    "logs/koala_bluez/*.json",
    "logs/killerkoala_voice/*.json",
    "/var/log/syslog",
    "/var/log/messages",
    "/var/log/kern.log",
]


def _read_tail(path: Path, max_lines: int) -> List[str]:
    try:
        if not path.exists() or not path.is_file():
            return []
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:]
    except Exception:
        return []


def _expand_logs(patterns: Iterable[str]) -> List[Path]:
    paths: List[Path] = []
    for pattern in patterns:
        matches = [Path(item) for item in glob.glob(pattern)]
        if not matches and not any(token in pattern for token in "*?["):
            matches = [Path(pattern)]
        for path in sorted(matches):
            if path not in paths:
                paths.append(path)
    return paths


def _collect_lines(patterns: Iterable[str], max_lines_per_file: int) -> List[str]:
    lines: List[str] = []
    for path in _expand_logs(patterns):
        lines.extend(_read_tail(path, max_lines_per_file))
    return lines


def _recent_guard_active(state_path: Path, cooldown_seconds: int) -> bool:
    if cooldown_seconds <= 0 or not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not bool(state.get("local_guard_enabled")):
            return False
        updated_at = float(state.get("updated_at", 0.0))
        return (time.time() - updated_at) < cooldown_seconds
    except Exception:
        return False


def run_loop(args: argparse.Namespace) -> int:
    patterns = args.log_glob or DEFAULT_LOG_GLOBS
    state_path = Path(args.state_path)
    interval = max(2.0, float(args.interval))
    while True:
        lines = _collect_lines(patterns, args.max_lines_per_file)
        award_xp = not args.no_award_xp and not _recent_guard_active(state_path, args.xp_cooldown)
        result = run_guard_once(
            metrics={},
            log_lines=lines,
            output_dir=args.output_dir,
            state_path=state_path,
            xp_path=args.xp_path,
            threshold=args.threshold,
            award_xp=award_xp,
        )
        print(json.dumps({
            "action": result.action_name,
            "status": result.status,
            "pressure_score": result.pressure_score,
            "local_guard_enabled": result.local_guard_enabled,
            "xp_reward": result.xp_reward if award_xp else 0,
            "guard_state": result.artifacts.get("guard_state"),
        }, sort_keys=True), flush=True)
        if args.once:
            return 0
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep the KoalaByte Blue 'that’s not a knife' BLE guard running")
    parser.add_argument("--interval", type=float, default=10.0, help="Seconds between guard passes")
    parser.add_argument("--threshold", type=int, default=5, help="Guard activation score")
    parser.add_argument("--xp-cooldown", type=int, default=300, help="Minimum seconds between XP awards while guard remains active")
    parser.add_argument("--max-lines-per-file", type=int, default=500)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    parser.add_argument("--log-glob", action="append", default=None, help="Log file or glob to inspect; may be supplied more than once")
    parser.add_argument("--no-award-xp", action="store_true")
    parser.add_argument("--once", action="store_true", help="Run one guard pass for smoke testing")
    args = parser.parse_args()
    try:
        return run_loop(args)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
