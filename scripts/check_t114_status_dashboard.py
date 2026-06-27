#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.t114_menu_status import status_label_description  # noqa: E402

STATUS_ROWS = [
    ("status:t114_link", "heltec_link"),
    ("status:t114_radio_gps", "radio_gps"),
    ("status:t114_tx", "lab_beacon_tx"),
]

DEFAULT_OUTPUT = ROOT / "logs" / "menu_actions" / "t114_status_dashboard_status.json"


def build_status() -> dict[str, object]:
    rows: dict[str, dict[str, str]] = {}
    for command, key in STATUS_ROWS:
        label, description = status_label_description(command)
        rows[key] = {"command": command, "label": label, "description": description}
    link_label = rows["heltec_link"]["label"]
    if link_label.endswith(": Connected"):
        hardware_state = "connected"
    elif link_label.endswith(": Waiting"):
        hardware_state = "waiting"
    else:
        hardware_state = "disconnected"
    return {
        "status": "T114_STATUS_DASHBOARD_READY",
        "hardware_state": hardware_state,
        "rows": rows,
        "active_status_check_attempted": True,
        "one_shot_installer_check": True,
        "updated_at": time.time(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check KoalaByte Blue T114 live status dashboard phrases")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path for status JSON artifact")
    parser.add_argument("--strict-connected", action="store_true", help="Fail unless Heltec Link reports Connected")
    args = parser.parse_args()

    payload = build_status()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.strict_connected and payload.get("hardware_state") != "connected":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
