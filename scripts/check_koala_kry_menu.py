#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

STATUS_PATH = ROOT / "logs" / "one_shot" / "koala_kry_menu_readiness.json"


def _commands() -> list[str]:
    prefix = "koala_kry_"
    return [
        prefix + "prompt_status",
        prefix + "use_latest_capture",
        prefix + "speed_live",
        prefix + "speed_fast",
        prefix + "speed_instant",
        prefix + "limit_50",
        prefix + "limit_200",
        prefix + "limit_all",
        prefix + "rf_review_on",
        prefix + "rf_review_off",
        prefix + "lab_ack_on",
        prefix + "owned_ack_on",
        prefix + "clear_prompt",
        prefix + "run_replay",
        prefix + "run_review",
    ]


def main() -> int:
    failures: list[str] = []
    try:
        from koalablue import koala_kry
        from koalablue.menu_catalog import leaf_menu_entries, menu_labels, submenu_title
        from koalablue.menu_action_runner import run_automated_menu_action
    except Exception as exc:
        failures.append(f"Koala Kry imports failed: {exc}")
        payload = {"status": "KOALA_KRY_MENU_INCOMPLETE", "failures": failures, "updated_at": time.time()}
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    labels = menu_labels("koala_kry")
    leaf_commands = {str(entry.get("command", "")) for entry in leaf_menu_entries()}
    required_commands = _commands()

    if submenu_title("koala_kry") != "Koala Kry":
        failures.append("Koala Kry submenu title is not registered")
    if len(labels) < 15:
        failures.append("Koala Kry submenu does not expose the expected prompt controls")
    for command in required_commands:
        if command not in leaf_commands:
            failures.append(f"Koala Kry catalog missing command: {command}")

    routed: dict[str, str] = {}
    for command in ["koala_kry_prompt_status", "koala_kry_speed_fast", "koala_kry_limit_50", "koala_kry_clear_prompt"]:
        result = run_automated_menu_action(command, command, "Bluetooth Tools")
        routed[command] = str(result.get("status"))
        if routed[command] != "AUTOMATED_ACTION_COMPLETE":
            failures.append(f"Koala Kry action did not route: {command}")

    prompt_state = koala_kry.load_prompt_state()
    payload = {
        "status": "KOALA_KRY_MENU_READY" if not failures else "KOALA_KRY_MENU_INCOMPLETE",
        "submenu_title": submenu_title("koala_kry"),
        "labels": labels,
        "required_commands": required_commands,
        "routed": routed,
        "prompt_path": str(koala_kry.DEFAULT_PROMPT_PATH),
        "prompt_keys": sorted(str(key) for key in prompt_state.keys()),
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
