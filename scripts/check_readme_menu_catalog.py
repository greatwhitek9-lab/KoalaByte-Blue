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

import koalablue  # noqa: F401 - installs dynamic GreatWhite Reef and TwoCan menus
from koalablue.menu_catalog import MAIN_MENU_ITEMS, SUBMENU_ITEMS, submenu_title  # noqa: E402

README_PATH = ROOT / "README.md"
STATUS_PATH = ROOT / "logs" / "menu_actions" / "readme_menu_catalog_status.json"


def _rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in MAIN_MENU_ITEMS:
        rows.append({
            "menu": "main",
            "menu_title": submenu_title("main"),
            "label": str(entry.get("label", "")),
            "command": str(entry.get("command", "")),
        })
    for menu_name, entries in SUBMENU_ITEMS.items():
        for entry in entries:
            rows.append({
                "menu": menu_name,
                "menu_title": submenu_title(menu_name),
                "label": str(entry.get("label", "")),
                "command": str(entry.get("command", "")),
            })
    return rows


def main() -> int:
    failures: list[str] = []
    readme = README_PATH.read_text(encoding="utf-8", errors="ignore") if README_PATH.exists() else ""
    if not readme:
        failures.append("README.md is missing or empty")

    checked_rows: list[dict[str, str]] = []
    skipped_dynamic_rows: list[dict[str, str]] = []
    for row in _rows():
        label = row["label"]
        command = row["command"]
        if command.startswith("greatwhite_pcap_read:"):
            skipped_dynamic_rows.append(row)
            continue
        checked_rows.append(row)
        if label and label not in readme:
            failures.append(f"README missing menu label [{row['menu']}]: {label}")
        if command and command not in readme:
            failures.append(f"README missing command key [{row['menu']}]: {command}")

    for marker in [
        "# Complete jungle menu reference",
        "TwoCan Read-Only Tools submenu",
        "GreatWhite Reef submenu",
        "PCAP N: `<filename>`",
        "greatwhite_pcap_read:<filename>",
        "KillerKoala voice commands",
        "Touchscreen selection",
        "K1-K8 button-board navigation",
        "USB or Bluetooth keyboard navigation",
    ]:
        if marker not in readme:
            failures.append(f"README missing required complete-menu marker: {marker}")

    payload = {
        "status": "README_MENU_CATALOG_COMPLETE" if not failures else "README_MENU_CATALOG_INCOMPLETE",
        "readme_path": str(README_PATH),
        "checked_static_rows": len(checked_rows),
        "dynamic_rows_skipped": len(skipped_dynamic_rows),
        "menu_names": ["main", *SUBMENU_ITEMS.keys()],
        "dynamic_row_policy": "Runtime-generated GreatWhite PCAP rows are represented by the documented PCAP N/<filename> pattern.",
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
