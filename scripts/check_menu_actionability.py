#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

# Never allow this validator to trigger host power actions.
os.environ["KOALABYTE_MENU_SHUTDOWN_DRY_RUN"] = "1"
os.environ["KOALABYTE_MENU_RESET_DRY_RUN"] = "1"
os.environ.setdefault("KOALABYTE_MESHTASTIC_LISTEN_SECONDS", "1")
os.environ.setdefault("KOALABYTE_MENU_KAPTURE_SECONDS", "2")
os.environ.setdefault("KOALABYTE_RF_BLE_LAB_TX_SECONDS", "2")

import koalablue  # noqa: E402,F401
from koalablue.menu_actionability import (  # noqa: E402
    MANIFEST_PATH,
    PLACEHOLDER_STATUSES,
    build_actionability_manifest,
)
from koalablue.menu_action_runner import run_automated_menu_action  # noqa: E402
from koalablue.menu_catalog import all_menu_entries  # noqa: E402


def placeholder_paths(value: Any, prefix: str = "payload") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        status = str(value.get("status", ""))
        if status in PLACEHOLDER_STATUSES or status.endswith("_ACTION_RECORDED"):
            paths.append(f"{prefix}.status={status}")
        for key, item in value.items():
            paths.extend(placeholder_paths(item, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(placeholder_paths(item, f"{prefix}[{index}]"))
    return paths


def nested_status(payload: dict[str, Any]) -> str:
    result = payload.get("result")
    return str(result.get("status", "")) if isinstance(result, dict) else ""


def main() -> int:
    failures: list[str] = []
    manifest, manifest_failures = build_actionability_manifest()
    failures.extend(manifest_failures)

    if manifest.get("status") != "MENU_ACTIONABILITY_READY":
        failures.append(f"unexpected manifest status: {manifest.get('status')}")
    if int(manifest.get("enabled_leaf_count", 0)) != int(manifest.get("concrete_enabled_leaf_count", -1)):
        failures.append(
            "enabled leaf count does not match concrete enabled leaf count: "
            f"{manifest.get('enabled_leaf_count')} != {manifest.get('concrete_enabled_leaf_count')}"
        )

    visible_placeholder_rows = []
    for entry in all_menu_entries():
        if not bool(entry.get("enabled", True)):
            continue
        text = f"{entry.get('label', '')} {entry.get('description', '')}".lower()
        if "placeholder" in text or "intentionally non-operational" in text:
            visible_placeholder_rows.append(
                {
                    "label": entry.get("label"),
                    "command": entry.get("command"),
                    "description": entry.get("description"),
                }
            )
    if visible_placeholder_rows:
        failures.append(f"visible placeholder wording remains: {visible_placeholder_rows}")

    expected_statuses = {
        "companion_status": {"COMPANION_READY", "COMPANION_READY_WITH_PHRASE_FALLBACK"},
        "killerkoala_hybrid": {"KILLERKOALA_HYBRID_READY", "KILLERKOALA_HYBRID_FALLBACK_READY"},
        "xp_status": {"XP_STATUS_READY"},
        "button_map": {"BUTTON_MAP_READY"},
        "firmware_version": {"FIRMWARE_VERSION_READY"},
        "location_gate_gnss_current": {"GNSS_FIX_READY", "GNSS_FIX_LOCKED_OR_UNAVAILABLE"},
        "koala_kapture_transmit_placeholder": {"RF_BLE_TRANSMIT_SAFETY_CHECK_COMPLETE"},
        "koala_kry_transmit_placeholder": {"RF_BLE_TRANSMIT_SAFETY_CHECK_COMPLETE"},
        "koala_kan_transmit_placeholder": {"CAN_TRANSMIT_SAFETY_CHECK_COMPLETE"},
        "keyboard:wigle_api_name": {"KEYBOARD_UI_ROUTE_READY"},
    }

    probe_results: dict[str, Any] = {}
    for command, allowed_statuses in expected_statuses.items():
        payload = run_automated_menu_action(command, label=f"audit:{command}", group="audit")
        probe_results[command] = payload
        placeholders = placeholder_paths(payload)
        if placeholders:
            failures.append(f"{command} returned placeholder paths: {placeholders}")
        status = nested_status(payload)
        if status not in allowed_statuses:
            failures.append(f"{command} returned nested status {status!r}; expected one of {sorted(allowed_statuses)}")

        result = payload.get("result")
        if command.endswith("transmit_placeholder") and isinstance(result, dict):
            if result.get("radio_action_performed") not in {None, False}:
                failures.append(f"{command} safety check unexpectedly performed a radio action")
            if result.get("can_action_performed") not in {None, False}:
                failures.append(f"{command} safety check unexpectedly performed a CAN action")

    unknown = run_automated_menu_action("definitely_missing_menu_command", "missing", "audit")
    if unknown.get("status") != "AUTOMATED_ACTION_SKIPPED":
        failures.append(f"unknown command did not fail closed: {unknown}")
    if "No concrete menu implementation" not in str(unknown.get("error", "")):
        failures.append(f"unknown command error is not explicit: {unknown}")

    output = {
        "status": "MENU_ACTIONABILITY_VALIDATED" if not failures else "MENU_ACTIONABILITY_FAILED",
        "manifest_path": str(MANIFEST_PATH),
        "menu_count": manifest.get("menu_count"),
        "entry_count": manifest.get("entry_count"),
        "enabled_leaf_count": manifest.get("enabled_leaf_count"),
        "concrete_enabled_leaf_count": manifest.get("concrete_enabled_leaf_count"),
        "probe_commands": sorted(probe_results),
        "failures": failures,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
