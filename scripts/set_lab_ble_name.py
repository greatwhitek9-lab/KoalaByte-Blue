#!/usr/bin/env python3
"""Set the KoalaByte Blue lab BLE device name in the nRF52840 DK config.

Usage:
    python3 scripts/set_lab_ble_name.py KoalaTag-Lab

The name is written to firmware/nrf52840-dk-lab-peripheral/prj.conf as
CONFIG_BT_DEVICE_NAME.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONF_PATH = Path("firmware/nrf52840-dk-lab-peripheral/prj.conf")
NAME_RE = re.compile(r"^[A-Za-z0-9 _.-]{1,26}$")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/set_lab_ble_name.py <name>", file=sys.stderr)
        return 2
    name = sys.argv[1].strip()
    if not NAME_RE.fullmatch(name):
        print("Name must be 1-26 chars using letters, numbers, spaces, underscore, dash, or dot.", file=sys.stderr)
        return 2
    text = CONF_PATH.read_text(encoding="utf-8")
    new_line = f'CONFIG_BT_DEVICE_NAME="{name}"'
    if "CONFIG_BT_DEVICE_NAME=" in text:
        text = re.sub(r'CONFIG_BT_DEVICE_NAME=".*"', new_line, text)
    else:
        text += "\n" + new_line + "\n"
    CONF_PATH.write_text(text, encoding="utf-8")
    print(f"Updated {CONF_PATH} -> {new_line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
