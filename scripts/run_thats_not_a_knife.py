#!/usr/bin/env python3
"""Run the KoalaByte Blue always-on BLE defense guard with the jungle/eucalyptus theme."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List

from koalablue.ble_defense_guard import (  # run_cli imported to keep legacy readiness text stable
    DEFAULT_BLOCK_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SETTINGS_PATH,
    DEFAULT_STATE_PATH,
    DEFAULT_XP_PATH,
    MONITOR_REGISTRY,
    load_monitor_settings,
    run_cli as _legacy_run_cli,
    run_guard_once,
    set_monitor_enabled,
    set_monitor_threshold,
)


def _json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _card(title: str, rows: Iterable[str]) -> None:
    try:
        from koalablue.menu_theme import render_terminal_eucalyptus_card

        print(render_terminal_eucalyptus_card(title, rows, subtitle="that’s not a knife"))
    except Exception:
        print(f"KoalaByte Blue :: that’s not a knife :: {title}")
        for row in rows:
            print(f"- {row}")


def _settings_rows(settings: dict) -> List[str]:
    rows = ["Individual BLE defensive monitors", ""]
    monitors = settings.get("monitors", {})
    for monitor_id in MONITOR_REGISTRY:
        spec = monitors.get(monitor_id, {})
        state = "ON " if bool(spec.get("enabled", True)) else "OFF"
        threshold = int(spec.get("threshold", MONITOR_REGISTRY[monitor_id]["threshold"]))
        display = str(spec.get("display_name", MONITOR_REGISTRY[monitor_id]["display_name"]))
        rows.append(f"{state} | {monitor_id:<13} | threshold {threshold:<2} | {display}")
    rows.extend([
        "",
        "Controls: enable <monitor> | disable <monitor> | threshold <monitor> <value>",
        "Aliases: dos, ble_dos, bluesnarf, blue_snarfing, bluesnarffing, mitm",
    ])
    return rows


def _result_rows(result) -> List[str]:
    rows = [
        f"Status: {result.status}",
        f"Local block: {'SUCCESS' if result.defensive_block_successful else 'not active'}",
        f"XP earned this pass: {result.xp_reward}",
        f"Active monitors: {', '.join(result.active_monitors) if result.active_monitors else 'none'}",
        f"Disabled monitors: {', '.join(result.disabled_monitors) if result.disabled_monitors else 'none'}",
        "",
        "Monitor scores:",
    ]
    for monitor_id in MONITOR_REGISTRY:
        rows.append(f"  {monitor_id:<13} {result.monitor_scores.get(monitor_id, 0)}")
    rows.extend(["", f"Alert: {result.companion_alert}"])
    return rows


def main() -> int:
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
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of the eucalyptus themed card")
    args = parser.parse_args()

    if args.command in {"status", "list"}:
        settings = load_monitor_settings(args.settings_path)
        _json(settings) if args.json else _card("Monitor settings", _settings_rows(settings))
        return 0

    if args.command == "enable":
        if not args.monitor:
            parser.error("enable requires a monitor id")
        settings = set_monitor_enabled(args.monitor, True, args.settings_path)
        _json(settings) if args.json else _card("Monitor enabled", _settings_rows(settings))
        return 0

    if args.command == "disable":
        if not args.monitor:
            parser.error("disable requires a monitor id")
        settings = set_monitor_enabled(args.monitor, False, args.settings_path)
        _json(settings) if args.json else _card("Monitor disabled", _settings_rows(settings))
        return 0

    if args.command == "threshold":
        if not args.monitor or args.value is None:
            parser.error("threshold requires a monitor id and integer value")
        settings = set_monitor_threshold(args.monitor, int(args.value), args.settings_path)
        _json(settings) if args.json else _card("Monitor threshold updated", _settings_rows(settings))
        return 0

    metrics = json.loads(args.metrics_json) if args.metrics_json else {}
    lines: List[str] = []
    if args.log_file:
        path = Path(args.log_file)
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]

    result = run_guard_once(
        metrics=metrics,
        log_lines=lines,
        output_dir=args.output_dir,
        state_path=args.state_path,
        block_path=args.block_path,
        settings_path=args.settings_path,
        xp_path=args.xp_path,
        threshold=args.threshold,
        award_xp=not args.no_award_xp,
    )
    _json(asdict(result)) if args.json else _card("Guard pass", _result_rows(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
