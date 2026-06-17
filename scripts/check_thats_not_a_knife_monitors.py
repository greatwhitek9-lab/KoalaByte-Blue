#!/usr/bin/env python3
"""Smoke checks for the KoalaByte Blue 'that’s not a knife' monitor toggles."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.ble_defense_guard import (  # noqa: E402
    MONITOR_REGISTRY,
    load_monitor_settings,
    run_guard_once,
    set_monitor_enabled,
)

EXPECTED = {"dos_pressure", "bluesnarfing", "bluebugging", "mitm_guard"}


def main() -> int:
    base = REPO_ROOT / "logs" / "readiness_thats_not_a_knife_monitors"
    settings_path = base / "monitor_settings.json"
    state_path = base / "guard_state.json"
    block_path = base / "block_state.json"
    xp_path = base / "xp_state.json"

    missing = EXPECTED.difference(MONITOR_REGISTRY)
    if missing:
        print(f"Missing monitors: {sorted(missing)}", file=sys.stderr)
        return 1

    settings = load_monitor_settings(settings_path)
    for monitor_id in EXPECTED:
        if monitor_id not in settings.get("monitors", {}):
            print(f"Missing monitor setting: {monitor_id}", file=sys.stderr)
            return 1

    set_monitor_enabled("bluesnarfing", False, settings_path)
    disabled = run_guard_once(
        log_lines=["pbap phonebook vcard file pull"],
        output_dir=base,
        state_path=state_path,
        block_path=block_path,
        settings_path=settings_path,
        xp_path=xp_path,
        award_xp=False,
    )
    if disabled.status != "MONITORING" or disabled.active_monitors:
        print("Disabled monitor still triggered", file=sys.stderr)
        return 1

    set_monitor_enabled("bluesnarfing", True, settings_path)
    enabled = run_guard_once(
        log_lines=["pbap phonebook vcard file pull"],
        output_dir=base,
        state_path=state_path,
        block_path=block_path,
        settings_path=settings_path,
        xp_path=xp_path,
        award_xp=False,
    )
    if "bluesnarfing" not in enabled.active_monitors or not enabled.defensive_block_successful:
        print("Enabled monitor did not complete a local defensive block", file=sys.stderr)
        return 1

    if enabled.xp_reward != 0 or enabled.xp_after != enabled.xp_before:
        print("XP changed during award_xp=False smoke check", file=sys.stderr)
        return 1

    print("that’s not a knife monitor toggle smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
