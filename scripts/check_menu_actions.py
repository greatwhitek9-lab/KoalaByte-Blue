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

from koalablue.menu_catalog import MAIN_MENU_ITEMS, SUBMENU_ITEMS, all_menu_entries, leaf_menu_entries, submenu_name_from_command  # noqa: E402
from scripts.run_menu_screen import make_menu  # noqa: E402

OUTPUT_DIR = ROOT / "logs" / "menu_actions"
MANIFEST_PATH = OUTPUT_DIR / "menu_action_manifest.json"
STATUS_PATH = OUTPUT_DIR / "menu_action_status.json"


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
        handler_name = ""
        routed = False
        automated = False

        if is_submenu:
            routed = submenu in menu_names
            automated = routed
            if enabled and not routed:
                failures.append(f"submenu item '{label}' points to missing submenu: {command}")
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
                "routed": routed,
                "automated_select": automated,
                "handler": handler_name,
                "description": entry.get("description", ""),
            }
        )

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
        "status_rows": status_rows,
        "handler_commands": handler_commands,
        "entries": rows,
        "one_shot_installer_safe": True,
        "no_menu_actions_executed": True,
        "notes": [
            "This is a readiness/manifest check only.",
            "It validates that every enabled menu leaf, including status rows, has an automated select handler.",
            "It does not run scans, open long-running actions, flash firmware, or start live activity.",
        ],
        "failures": failures,
    }
    return manifest, failures


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest, failures = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    STATUS_PATH.write_text(
        json.dumps(
            {
                "status": manifest["status"],
                "updated_at": manifest["updated_at"],
                "manifest": str(MANIFEST_PATH),
                "enabled_leaf_count": manifest["enabled_leaf_count"],
                "status_row_count": manifest["status_row_count"],
                "handler_count": manifest["handler_count"],
                "failures": failures,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": manifest["status"], "manifest": str(MANIFEST_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
