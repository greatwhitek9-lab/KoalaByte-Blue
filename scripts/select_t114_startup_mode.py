#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import select
import sys
import time
from pathlib import Path

MODES = {
    "lab": {
        "mode": "heltec_lab",
        "title": "Heltec Lab / mouth / BLE / GNSS",
        "helper": "scripts/flash_heltec_mouth.sh",
    },
    "konnect": {
        "mode": "koala_konnect_t114",
        "title": "Koala Konnect T114",
        "helper": "scripts/flash_koala_konnect_t114.sh",
    },
}
ALIASES = {
    "1": "lab", "l": "lab", "lab": "lab", "heltec": "lab", "normal": "lab", "default": "lab",
    "2": "konnect", "k": "konnect", "konnect": "konnect", "koala": "konnect", "koala konnect": "konnect",
}


def resolve_mode(value: str, default: str) -> str:
    key = ALIASES.get(value.strip().lower().replace("_", " ").replace("-", " "), "")
    return key if key in MODES else default


def prompt(default: str, timeout: float) -> str:
    if not sys.stdin.isatty():
        return default
    print()
    print("KoalaByte Blue T114 Startup Mode Selector")
    print("==========================================")
    print("Target: Heltec Mesh Node T114 v2 onboard nRF52840")
    print("1) Heltec Lab / mouth / BLE / GNSS")
    print("2) Koala Konnect T114")
    print(f"Press 1/L for Lab, 2/K for Konnect, or Enter for default: {MODES[default]['title']}")
    print(f"Auto-selects default in {timeout:.0f} seconds.")
    print("Selection> ", end="", flush=True)
    ready, _, _ = select.select([sys.stdin], [], [], max(0.0, timeout))
    if not ready:
        print()
        return default
    return resolve_mode(sys.stdin.readline().strip(), default)


def main() -> int:
    parser = argparse.ArgumentParser(description="Choose the Heltec T114 startup profile")
    parser.add_argument("--mode", default="", help="lab or konnect")
    parser.add_argument("--default-mode", default="lab", help="lab or konnect")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--state-path", default="logs/t114_profiles/startup_selection.json")
    args = parser.parse_args()

    default = resolve_mode(args.default_mode, "lab")
    selected = resolve_mode(args.mode, default) if args.mode else prompt(default, args.timeout)
    spec = MODES[selected]
    path = Path(args.state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "selected",
        "selected_key": selected,
        "selected_mode": spec["mode"],
        "selected_title": spec["title"],
        "helper": spec["helper"],
        "hardware_target": "Heltec Mesh Node T114 v2 onboard nRF52840",
        "updated_at": time.time(),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
