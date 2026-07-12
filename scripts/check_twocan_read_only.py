#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

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
from koalablue import twocan_read_only as twocan  # noqa: E402
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
    "TwoCan Clear Codes Safety Note",
]


class _FakeResponse:
    value = 123
    unit = "test"
    messages: list[str] = []

    def is_null(self) -> bool:
        return False


class _FakeConnection:
    def __init__(self) -> None:
        self.queries: list[object] = []

    def supports(self, _command: object) -> bool:
        return True

    def query(self, command: object, force: bool = False) -> _FakeResponse:
        self.queries.append((command, force))
        return _FakeResponse()


def _exercise_read_only_allowlist(failures: list[str]) -> dict[str, object]:
    safe_command = object()
    clear_command = object()
    fake_obd = SimpleNamespace(commands=SimpleNamespace(RPM=safe_command, CLEAR_DTC=clear_command))
    connection = _FakeConnection()

    allowed = twocan._query_named(fake_obd, connection, "RPM")
    if allowed.get("blocked") or not connection.queries:
        failures.append("explicitly allowlisted RPM query did not execute through the read-only path")

    query_count = len(connection.queries)
    blocked = twocan._query_named(fake_obd, connection, "CLEAR_DTC", force=True)
    if not blocked.get("blocked"):
        failures.append("CLEAR_DTC was not blocked by the TwoCan read-only allowlist")
    if len(connection.queries) != query_count:
        failures.append("CLEAR_DTC reached the adapter query path")

    unknown = twocan._query_named(fake_obd, connection, "SECURITY_ACCESS", force=True)
    if not unknown.get("blocked"):
        failures.append("non-allowlisted security-access command was not blocked")

    return {
        "allowed_query": allowed,
        "blocked_clear": blocked,
        "blocked_security": unknown,
        "adapter_query_count": len(connection.queries),
    }


def _exercise_offline_review(failures: list[str]) -> dict[str, object]:
    previous = os.environ.get("KOALABYTE_TWOCAN_CAPTURE_PATH")
    try:
        with tempfile.TemporaryDirectory(prefix="koalabyte-twocan-") as temp_dir:
            capture = Path(temp_dir) / "sample.candump"
            capture.write_text(
                "can0 123#01020304\ncan0 123#05060708\ncan0 456 [2] AA BB\n",
                encoding="utf-8",
            )
            os.environ["KOALABYTE_TWOCAN_CAPTURE_PATH"] = str(capture)
            result = twocan.offline_capture_review()
            if result.get("frame_count") != 3:
                failures.append(f"offline capture review parsed {result.get('frame_count')} frames; expected 3")
            if result.get("replay_performed") is not False:
                failures.append("offline capture review did not explicitly report replay_performed=False")
            if result.get("raw_transmit_performed") is not False:
                failures.append("offline capture review did not explicitly report raw_transmit_performed=False")
            return result
    finally:
        if previous is None:
            os.environ.pop("KOALABYTE_TWOCAN_CAPTURE_PATH", None)
        else:
            os.environ["KOALABYTE_TWOCAN_CAPTURE_PATH"] = previous


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
    if "twocan_clear_codes_safety_note" not in commands:
        failures.append("TwoCan submenu missing executable clear-codes safety-note action")

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
        elif match.command not in {*TWOCAN_COMMANDS, "twocan_clear_codes_safety_note"}:
            failures.append(f"voice launcher routed {label} to unexpected command: {match.command}")

    runner = make_menu()
    handler_names = getattr(runner, "_handlers", {})
    for command in (*TWOCAN_COMMANDS, "twocan_clear_codes_safety_note"):
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

    allowlist_test = _exercise_read_only_allowlist(failures)
    offline_review_test = _exercise_offline_review(failures)

    payload = {
        "status": "TWOCAN_READ_ONLY_READY" if not failures else "TWOCAN_READ_ONLY_INCOMPLETE",
        "submenu": SUBMENU_NAME,
        "labels": REQUIRED_LABELS,
        "commands": [*TWOCAN_COMMANDS, "twocan_clear_codes_safety_note"],
        "control_paths": ["voice", "touchscreen", "K1-K8 button board", "USB/Bluetooth keyboard"],
        "jungle_theme_checked": True,
        "read_only_allowlist_test": allowlist_test,
        "offline_capture_test": {
            "status": offline_review_test.get("status"),
            "frame_count": offline_review_test.get("frame_count"),
            "replay_performed": offline_review_test.get("replay_performed"),
            "raw_transmit_performed": offline_review_test.get("raw_transmit_performed"),
        },
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
