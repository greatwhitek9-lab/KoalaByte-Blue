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

import koalablue  # noqa: F401 - installs dynamic menu extensions
from koalablue.menu_catalog import SUBMENU_ITEMS, menu_labels  # noqa: E402
from koalablue.menu_theme import render_terminal_jungle_menu  # noqa: E402
from koalablue.menu_voice_launcher import parse_menu_voice_launch  # noqa: E402
from koalablue.twocan_read_only import SUBMENU_NAME, TWOCAN_COMMANDS  # noqa: E402
from scripts.run_menu_screen import make_menu, open_submenu  # noqa: E402

STATUS_PATH = ROOT / "logs" / "twocan_vehicle_diagnostics" / "twocan_read_only_readiness.json"
REQUIRED_LABELS = [
    "Run Full Read-Only Scan",
    "Adapter Identity",
    "Vehicle VIN and Calibration",
    "Stored DTC Report",
    "Pending DTC Report",
    "Permanent DTC Report",
    "Freeze-Frame Snapshot",
    "Readiness Monitors",
    "Live PID Snapshot",
    "Live PID Log 30 Seconds",
    "Offline CAN Capture Review",
    "Repair Verification Checklist",
]


def main() -> int:
    failures: list[str] = []
    labels = set(menu_labels(SUBMENU_NAME))
    commands = {str(row.get("command", "")) for row in SUBMENU_ITEMS.get(SUBMENU_NAME, [])}
    for label in REQUIRED_LABELS:
        if label not in labels:
            failures.append(f"TwoCan submenu missing label: {label}")
    for command in TWOCAN_COMMANDS:
        if command not in commands:
            failures.append(f"TwoCan submenu missing executable command: {command}")

    koala_kan_commands = {str(row.get("command", "")) for row in SUBMENU_ITEMS.get("koala_kan", [])}
    if f"submenu:{SUBMENU_NAME}" not in koala_kan_commands:
        failures.append("Koala Kan Kommander does not open the TwoCan read-only submenu")

    menu = make_menu()
    if not open_submenu(menu, f"submenu:{SUBMENU_NAME}"):
        failures.append("TwoCan submenu could not be opened through the shared menu path")
    else:
        for index in range(len(menu.items)):
            menu.selected_index = index
            menu._clamp_scroll_to_selection()
            rendered = render_terminal_jungle_menu(menu)
            for line_no, line in enumerate(rendered.splitlines(), start=1):
                if len(line) > 74:
                    failures.append(f"TwoCan jungle menu line {line_no} exceeds the text border")

    for label in REQUIRED_LABELS:
        match = parse_menu_voice_launch(f"killerkoala run {label}")
        if match is None:
            failures.append(f"voice launcher cannot resolve: {label}")
        elif match.command not in TWOCAN_COMMANDS:
            failures.append(f"voice launcher routed {label} to unexpected command: {match.command}")

    runner = make_menu()
    handler_names = getattr(runner, "_handlers", {})
    for command in TWOCAN_COMMANDS:
        if command not in handler_names:
            failures.append(f"shared touch/button/keyboard menu handler missing: {command}")

    module_path = ROOT / "pi-companion" / "koalablue" / "twocan_read_only.py"
    module_text = module_path.read_text(encoding="utf-8", errors="ignore") if module_path.exists() else ""
    for marker in [
        "READ_ONLY_SERVICE_NAMES",
        "FORBIDDEN_COMMAND_NAMES",
        '"CLEAR_DTC"',
        '"twocan_live_pid_log_30s"',
        '"twocan_offline_capture_review"',
        '"captured_traffic_replay_enabled"',
        '"voice_command_compatible"',
        '"touchscreen_compatible"',
        '"gpio_button_compatible"',
        '"keyboard_compatible"',
    ]:
        if marker not in module_text:
            failures.append(f"TwoCan module missing safety/control marker: {marker}")

    payload = {
        "status": "TWOCAN_READ_ONLY_READY" if not failures else "TWOCAN_READ_ONLY_INCOMPLETE",
        "submenu": SUBMENU_NAME,
        "labels": REQUIRED_LABELS,
        "commands": list(TWOCAN_COMMANDS),
        "control_paths": ["voice", "touchscreen", "K1-K8 button board", "USB/Bluetooth keyboard"],
        "jungle_theme_checked": True,
        "read_only": True,
        "excluded": [
            "DTC clearing",
            "ECU coding",
            "actuator tests",
            "security access and seed/key workflows",
            "OEM raw frame injection",
            "captured traffic replay",
            "synthetic ECU/UDS simulators",
        ],
        "updated_at": time.time(),
        "failures": failures,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
