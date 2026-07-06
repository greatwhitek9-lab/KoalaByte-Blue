#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.menu_catalog import MAIN_MENU_ITEMS, SUBMENU_ITEMS, all_menu_entries, leaf_menu_entries, menu_labels, submenu_name_from_command  # noqa: E402
from koalablue.menu_theme import DEFAULT_JUNGLE_MENU_THEME, GRAPHICAL_DESCRIPTION_MAX_LINES, GRAPHICAL_LABEL_MAX_LINES, render_terminal_jungle_menu  # noqa: E402
from scripts.run_menu_screen import make_menu, open_submenu  # noqa: E402

OUTPUT_DIR = ROOT / "logs" / "menu_actions"
MANIFEST_PATH = OUTPUT_DIR / "menu_action_manifest.json"
STATUS_PATH = OUTPUT_DIR / "menu_action_status.json"
TERMINAL_FRAME_WIDTH = 74

ALLOWED_DUPLICATE_COMMANDS = {
    "koala_kry_run_review",
    "koala_bluez_info",
    "koala_bluez_services",
    "koala_bluez_gatt_readiness",
    "bluez_outback_radio_ledger",
    "bluez_classic_track_finder",
    "bluez_treehouse_rfcomm_wiremap",
    "bluez_pouch_link_echo",
    "bluez_gumnut_gatt_ghostmap",
    "bluez_platypus_bt_proxy",
    "location_gate_status",
    "keyboard:bluez_lab_target",
    "bluez_lab_scope_status",
    "bluez_lab_owned_on",
    "bluez_lab_owned_off",
    "bluez_lab_scope_clear",
    "lab_transmit_policy_status",
    "lab_transmit_rf_ble_gated_lab",
    "lab_transmit_rf_ble_listen_only",
    "lab_transmit_rf_ble_disabled",
    "lab_transmit_rf_ble_arm_on",
    "lab_transmit_rf_ble_arm_off",
    "lab_transmit_rf_ble_passive_only",
    "lab_transmit_rf_ble_disabled_install",
}
BUILT_IN_UI_COMMANDS = {"quit"}

REQUIRED_KOALA_KAN_LABELS = [
    "Run Full Kan Check",
    "Kan Manifest",
    "Detect CAN Interfaces",
    "CAN0 Status",
    "Listen 10 Seconds",
    "Generate Bench Payloads",
    "Write CAN Bench Report",
    "TwoCan Vehicle Diagnostics",
    "TwoCan Clear Codes Safety Note",
    "Lab Transmit Policy Status",
    "CAN Mode: Gated Bench",
    "CAN Mode: Listen Only",
    "CAN Mode: Disabled",
    "Bench Simulator Confirm ON",
    "Bench Simulator Confirm OFF",
    "Transmit Safety Check",
    "Bench Transmit Gate",
    "Listen + Bench Transmit Gate",
]

REQUIRED_KOALA_KAN_COMMANDS = [
    "koala_kan_kommander",
    "koala_kan_manifest",
    "koala_kan_inventory",
    "koala_kan_status",
    "koala_kan_listen_10s",
    "koala_kan_generate_payloads",
    "koala_kan_report",
    "twocan_vehicle_diagnostics",
    "twocan_clear_codes_safety_note",
    "lab_transmit_policy_status",
    "lab_transmit_can_gated_bench",
    "lab_transmit_can_listen_only",
    "lab_transmit_can_disabled",
    "lab_transmit_bench_arm_on",
    "lab_transmit_bench_arm_off",
    "koala_kan_transmit_placeholder",
    "koala_kan_transmit_gate",
    "koala_kan_listen_transmit_gate",
]

REQUIRED_KOALA_KAPTURE_LABELS = [
    "Kapture Policy Status",
    "RF/BLE Mode: Gated Lab",
    "RF/BLE Mode: Listen Only",
    "RF/BLE Mode: Disabled",
    "RF/BLE Lab Confirm ON",
    "RF/BLE Lab Confirm OFF",
    "Kapture Listen Gate",
    "Kapture Transmit Safety Check",
    "Kapture Transmit Gate",
    "Kapture Listen + Transmit Gate",
]

REQUIRED_KOALA_KAPTURE_COMMANDS = [
    "lab_transmit_policy_status",
    "lab_transmit_rf_ble_gated_lab",
    "lab_transmit_rf_ble_listen_only",
    "lab_transmit_rf_ble_disabled",
    "lab_transmit_rf_ble_arm_on",
    "lab_transmit_rf_ble_arm_off",
    "koala_kapture_listen_gate",
    "koala_kapture_transmit_placeholder",
    "koala_kapture_transmit_gate",
    "koala_kapture_listen_transmit_gate",
]

REQUIRED_KOALA_KRY_POLICY_LABELS = [
    "Kry Policy Status",
    "RF/BLE Mode: Gated Lab",
    "RF/BLE Mode: Listen Only",
    "RF/BLE Mode: Disabled",
    "RF/BLE Lab Confirm ON",
    "RF/BLE Lab Confirm OFF",
    "Kry Listen Gate",
    "Kry Transmit Safety Check",
    "Kry Transmit Gate",
    "Kry Listen + Transmit Gate",
]

REQUIRED_LAB_TRANSMIT_LABELS = [
    "RF/BLE Mode: Gated Lab",
    "RF/BLE Mode: Listen Only",
    "RF/BLE Mode: Disabled",
    "RF/BLE Lab Confirm ON",
    "RF/BLE Lab Confirm OFF",
]

REQUIRED_LAB_TRANSMIT_COMMANDS = [
    "lab_transmit_rf_ble_gated_lab",
    "lab_transmit_rf_ble_listen_only",
    "lab_transmit_rf_ble_disabled",
    "lab_transmit_rf_ble_arm_on",
    "lab_transmit_rf_ble_arm_off",
]

LAB_TRANSMIT_COMMANDS = [
    "lab_transmit_policy_status",
    "lab_transmit_can_gated_bench",
    "lab_transmit_can_listen_only",
    "lab_transmit_can_disabled",
    "lab_transmit_bench_arm_on",
    "lab_transmit_bench_arm_off",
    "lab_transmit_rf_ble_gated_lab",
    "lab_transmit_rf_ble_listen_only",
    "lab_transmit_rf_ble_disabled",
    "lab_transmit_rf_ble_arm_on",
    "lab_transmit_rf_ble_arm_off",
    "lab_transmit_rf_ble_passive_only",
    "lab_transmit_rf_ble_disabled_install",
]

REQUIRED_RF_BLE_PERMISSION_VALUES = {
    "rf_ble_live_transmit": True,
    "synthetic_lab_transmit": True,
    "saved_signal_replay": True,
    "saved_signal_replay_scope": "offline_saved_artifact_replay",
    "captured_metadata_replay": True,
    "captured_signal_replay": False,
    "over_air_signal_replay": False,
}


def _command(entry: dict[str, Any]) -> str:
    return str(entry.get("command", "")).strip()


def _label(entry: dict[str, Any]) -> str:
    return str(entry.get("label", "")).strip()


def _enabled(entry: dict[str, Any]) -> bool:
    return bool(entry.get("enabled", True))


def _menu_names() -> set[str]:
    return {"main", *SUBMENU_ITEMS.keys()}


def _walk_menu_entries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in MAIN_MENU_ITEMS:
        rows.append({"menu": "main", **entry})
    for menu_name, entries in SUBMENU_ITEMS.items():
        for entry in entries:
            rows.append({"menu": menu_name, **entry})
    return rows


def _visible_duplicate_commands() -> dict[str, list[str]]:
    seen: dict[str, list[str]] = {}
    for entry in _walk_menu_entries():
        if not _enabled(entry):
            continue
        command = _command(entry)
        if not command or command.startswith("submenu:") or command in BUILT_IN_UI_COMMANDS:
            continue
        seen.setdefault(command, []).append(_label(entry))
    return {command: labels for command, labels in seen.items() if len(set(labels)) > 1}


def _check_terminal_theme_fit(menu_names: set[str]) -> list[str]:
    failures: list[str] = []
    for menu_name in sorted(menu_names):
        menu = make_menu()
        if menu_name != "main":
            open_submenu(menu, f"submenu:{menu_name}")
        text = render_terminal_jungle_menu(menu)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if len(line) > TERMINAL_FRAME_WIDTH:
                failures.append(f"{menu_name} terminal theme line {line_no} exceeds {TERMINAL_FRAME_WIDTH} chars")
    return failures


def _validate_koala_kan_actions() -> list[str]:
    failures: list[str] = []
    labels = set(menu_labels("koala_kan"))
    commands = {str(entry.get("command", "")) for entry in SUBMENU_ITEMS.get("koala_kan", [])}
    for label in REQUIRED_KOALA_KAN_LABELS:
        if label not in labels:
            failures.append(f"Koala Kan submenu missing label: {label}")
    for command in REQUIRED_KOALA_KAN_COMMANDS:
        if command not in commands:
            failures.append(f"Koala Kan submenu missing command: {command}")

    runner_path = ROOT / "pi-companion" / "koalablue" / "menu_action_runner.py"
    runner_text = runner_path.read_text(encoding="utf-8", errors="ignore") if runner_path.exists() else ""
    required_runner_needles = [
        "def _koala_kan",
        "def _twocan_vehicle_diagnostics",
        "def _lab_transmit_policy",
        "lab_transmit_policy.run_menu_action",
        "lab_transmit_policy.can_transmit_gate_status",
        "lab_transmit_policy.blocked_transmit_action",
        "kan.manifest",
        "kan.inventory",
        "kan.status",
        "kan.listen",
        "kan.generate_payloads",
        "kan.report",
        "kan.blocked_transmit_placeholder",
        "kan.transmit",
        "kan.listen_transmit",
        "twocan.readiness",
        "twocan.clear_codes_safety_note",
    ] + [command for command in REQUIRED_KOALA_KAN_COMMANDS if not command.startswith("lab_transmit_")]
    for needle in required_runner_needles:
        if needle not in runner_text:
            failures.append(f"menu_action_runner.py missing Koala Kan/TwoCan backend marker: {needle}")

    twocan_path = ROOT / "pi-companion" / "koalablue" / "vehicle_diagnostics_readiness.py"
    twocan_text = twocan_path.read_text(encoding="utf-8", errors="ignore") if twocan_path.exists() else ""
    for needle in ["TwoCan Vehicle Diagnostics", "clear_codes_enabled", "False", "No diagnostic trouble code clearing"]:
        if needle not in twocan_text:
            failures.append(f"TwoCan helper missing safety marker: {needle}")
    return failures


def _validate_kapture_kry_actions() -> list[str]:
    failures: list[str] = []
    kapture_labels = set(menu_labels("koala_kapture"))
    kapture_commands = {str(entry.get("command", "")) for entry in SUBMENU_ITEMS.get("koala_kapture", [])}
    for label in REQUIRED_KOALA_KAPTURE_LABELS:
        if label not in kapture_labels:
            failures.append(f"Koala Kapture submenu missing label: {label}")
    for command in REQUIRED_KOALA_KAPTURE_COMMANDS:
        if command not in kapture_commands:
            failures.append(f"Koala Kapture submenu missing command: {command}")

    kry_labels = set(menu_labels("koala_kry"))
    for label in REQUIRED_KOALA_KRY_POLICY_LABELS:
        if label not in kry_labels:
            failures.append(f"Koala Kry submenu missing RF/BLE policy label: {label}")

    permissions_json = ROOT / "config" / "rf_ble_lab_permissions.json"
    if not permissions_json.exists():
        failures.append("missing RF/BLE lab permissions manifest: config/rf_ble_lab_permissions.json")
    else:
        try:
            payload = json.loads(permissions_json.read_text(encoding="utf-8"))
            for key, expected in REQUIRED_RF_BLE_PERMISSION_VALUES.items():
                if payload.get(key) != expected:
                    failures.append(f"RF/BLE permission manifest has {key}={payload.get(key)!r}; expected {expected!r}")
        except Exception as exc:
            failures.append(f"RF/BLE permission manifest is not valid JSON: {exc}")

    permissions_module = ROOT / "pi-companion" / "koalablue" / "rf_ble_lab_permissions.py"
    permissions_text = permissions_module.read_text(encoding="utf-8", errors="ignore") if permissions_module.exists() else ""
    for needle in [
        "RF_BLE_LAB_PERMISSIONS",
        "def permission_manifest",
        "rf_ble_live_transmit",
        "synthetic_lab_transmit",
        "saved_signal_replay",
        "offline_saved_artifact_replay",
        "captured_metadata_replay",
        "captured_signal_replay",
        "over_air_signal_replay",
    ]:
        if needle not in permissions_text:
            failures.append(f"rf_ble_lab_permissions.py missing marker: {needle}")
    return failures


def _validate_lab_transmit_actions() -> list[str]:
    failures: list[str] = []
    lab_labels = set(menu_labels("lab"))
    lab_commands = {str(entry.get("command", "")) for entry in SUBMENU_ITEMS.get("lab", [])}
    for label in REQUIRED_LAB_TRANSMIT_LABELS:
        if label not in lab_labels:
            failures.append(f"Lab submenu missing lab-transmit label: {label}")
    for command in REQUIRED_LAB_TRANSMIT_COMMANDS:
        if command not in lab_commands:
            failures.append(f"Lab submenu missing lab-transmit command: {command}")

    policy_path = ROOT / "pi-companion" / "koalablue" / "lab_transmit_policy.py"
    policy_text = policy_path.read_text(encoding="utf-8", errors="ignore") if policy_path.exists() else ""
    for needle in [
        "def write_policy",
        "def policy_status",
        "def set_can_mode",
        "def set_rf_ble_mode",
        "def set_bench_arm",
        "def set_rf_ble_arm",
        "def can_transmit_gate_status",
        "def rf_ble_transmit_gate_status",
        "def blocked_transmit_action",
        "def blocked_rf_ble_action",
        "def run_menu_action",
        "no_dtc_clear_or_ecu_coding",
        "no_captured_traffic_replay",
    ] + LAB_TRANSMIT_COMMANDS:
        if needle not in policy_text:
            failures.append(f"lab_transmit_policy.py missing marker: {needle}")
    return failures


def build_manifest() -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    menu_names = _menu_names()
    menu = make_menu()
    handlers = getattr(menu, "_handlers", {})
    rows = []

    for entry in _walk_menu_entries():
        command = _command(entry)
        label = _label(entry)
        enabled = _enabled(entry)
        submenu = submenu_name_from_command(command)
        is_submenu = bool(submenu)
        is_status_row = command.startswith("status:")
        is_builtin_ui_command = command in BUILT_IN_UI_COMMANDS
        handler_name = "built_in_ui" if is_builtin_ui_command else ""
        routed = False
        automated = False

        if is_submenu:
            routed = submenu in menu_names
            automated = routed
            if enabled and not routed:
                failures.append(f"submenu item '{label}' points to missing submenu: {command}")
        elif enabled and is_builtin_ui_command:
            routed = True
            automated = True
        elif enabled:
            handler = handlers.get(command)
            routed = handler is not None
            automated = routed
            handler_name = getattr(handler, "__name__", "") if handler is not None else ""
            if not routed:
                failures.append(f"enabled menu item '{label}' has no automated select handler: {command}")
        else:
            routed = True
            automated = True

        rows.append(
            {
                "menu": entry.get("menu", "main"),
                "group": entry.get("group", ""),
                "label": label,
                "command": command,
                "enabled": enabled,
                "submenu": submenu,
                "is_submenu": is_submenu,
                "is_status_row": is_status_row,
                "is_builtin_ui_command": is_builtin_ui_command,
                "routed": routed,
                "automated_select": automated,
                "handler": handler_name,
                "description": entry.get("description", ""),
            }
        )

    theme = DEFAULT_JUNGLE_MENU_THEME
    if "jungle" not in theme.border_style or "eucalyptus" not in theme.border_style:
        failures.append("menu theme no longer carries the jungle/eucalyptus border identity")
    if theme.font_family != theme.item_font_family:
        failures.append("menu title/item font stacks diverged")
    if GRAPHICAL_LABEL_MAX_LINES != 1:
        failures.append("graphical labels must be constrained to one line")
    if GRAPHICAL_DESCRIPTION_MAX_LINES > 2:
        failures.append("graphical descriptions must stay within two lines")
    failures.extend(_check_terminal_theme_fit(menu_names))

    duplicate_commands = _visible_duplicate_commands()
    unexpected_duplicates = sorted(set(duplicate_commands) - ALLOWED_DUPLICATE_COMMANDS)
    for command in unexpected_duplicates:
        failures.append(f"unexpected duplicate visible command '{command}': {duplicate_commands[command]}")

    failures.extend(_validate_koala_kan_actions())
    failures.extend(_validate_kapture_kry_actions())
    failures.extend(_validate_lab_transmit_actions())

    leaf_commands = sorted({_command(entry) for entry in leaf_menu_entries()})
    status_rows = sorted({_command(entry) for entry in leaf_menu_entries() if _command(entry).startswith("status:")})
    handler_commands = sorted(str(command) for command in handlers.keys())
    manifest = {
        "status": "MENU_ACTIONS_READY" if not failures else "MENU_ACTIONS_INCOMPLETE",
        "updated_at": time.time(),
        "menu_count": len(menu_names),
        "menu_names": sorted(menu_names),
        "total_entries": len(rows),
        "catalog_entry_count": len(all_menu_entries()),
        "enabled_leaf_count": len(leaf_commands),
        "status_row_count": len(status_rows),
        "handler_count": len(handler_commands),
        "leaf_commands": leaf_commands,
        "handler_commands": handler_commands,
        "built_in_ui_commands": sorted(BUILT_IN_UI_COMMANDS),
        "koala_kan_required_labels": REQUIRED_KOALA_KAN_LABELS,
        "koala_kan_required_commands": REQUIRED_KOALA_KAN_COMMANDS,
        "koala_kapture_required_labels": REQUIRED_KOALA_KAPTURE_LABELS,
        "koala_kapture_required_commands": REQUIRED_KOALA_KAPTURE_COMMANDS,
        "koala_kry_policy_required_labels": REQUIRED_KOALA_KRY_POLICY_LABELS,
        "rf_ble_permission_manifest": REQUIRED_RF_BLE_PERMISSION_VALUES,
        "lab_transmit_required_labels": REQUIRED_LAB_TRANSMIT_LABELS,
        "lab_transmit_required_commands": REQUIRED_LAB_TRANSMIT_COMMANDS,
        "rows": rows,
        "theme": {
            "title": theme.title,
            "font_family": theme.font_family,
            "item_font_family": theme.item_font_family,
            "border_style": theme.border_style,
            "graphical_label_max_lines": GRAPHICAL_LABEL_MAX_LINES,
            "graphical_description_max_lines": GRAPHICAL_DESCRIPTION_MAX_LINES,
            "terminal_frame_width": TERMINAL_FRAME_WIDTH,
        },
        "visible_duplicate_commands": duplicate_commands,
        "allowed_duplicate_commands": sorted(ALLOWED_DUPLICATE_COMMANDS),
        "failures": failures,
    }
    return manifest, failures


def main() -> int:
    manifest, failures = build_manifest()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    STATUS_PATH.write_text(json.dumps({"status": manifest["status"], "manifest_path": str(MANIFEST_PATH), "failures": failures, "updated_at": manifest["updated_at"]}, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "manifest_path": str(MANIFEST_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
