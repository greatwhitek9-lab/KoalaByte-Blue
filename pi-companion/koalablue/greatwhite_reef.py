from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

SUBMENU_NAME = "greatwhite_reef"
GROUP_NAME = "GreatWhite Reef"
OUTPUT_DIR = Path("logs/greatwhite_reef")
PCAP_DIR = OUTPUT_DIR / "pcaps"
STATUS_PATH = OUTPUT_DIR / "greatwhite_reef_status.json"
MAX_DYNAMIC_PCAP_ROWS = 20

GREATWHITE_REEF_COMMANDS: tuple[str, ...] = (
    "greatwhite_reef_status",
    "greatwhite_tigershark_check",
    "greatwhite_tigershark_interfaces",
    "greatwhite_tigershark_pcap_folder",
    "greatwhite_tigershark_read_latest",
    "great_wire_shark_launch_notes",
    "great_wire_shark_folder_notes",
    "greatwhite_reef_report",
)


def _is_greatwhite_command(command: str) -> bool:
    return command in GREATWHITE_REEF_COMMANDS or command.startswith("greatwhite_pcap_read:")


def _menu_rows() -> list[dict[str, object]]:
    from .menu_catalog import _item

    rows: list[dict[str, object]] = [
        _item(GROUP_NAME, "Reef Status", "greatwhite_reef_status", "Show TigerShark and Great Wire Shark readiness"),
        _item(GROUP_NAME, "TigerShark Install Check", "greatwhite_tigershark_check", "Check tshark availability"),
        _item(GROUP_NAME, "TigerShark Interfaces", "greatwhite_tigershark_interfaces", "List local tshark interfaces for lab planning"),
        _item(GROUP_NAME, "TigerShark PCAP Folder", "greatwhite_tigershark_pcap_folder", "Create, sync, and show the local PCAP review folder"),
        _item(GROUP_NAME, "TigerShark Read Latest PCAP", "greatwhite_tigershark_read_latest", "Summarize the newest local PCAP/PCAPNG file"),
    ]
    for index, path in enumerate(_pcap_files(), start=1):
        label = f"PCAP {index}: {path.name}"
        rows.append(_item(GROUP_NAME, label, f"greatwhite_pcap_read:{path.name}", "Run this selected PCAP through TigerShark Read"))
    rows.extend([
        _item(GROUP_NAME, "Great Wire Shark Launch Notes", "great_wire_shark_launch_notes", "Write Wireshark GUI review notes"),
        _item(GROUP_NAME, "Great Wire Shark Folder Notes", "great_wire_shark_folder_notes", "Write folder review notes for Great Wire Shark"),
        _item(GROUP_NAME, "GreatWhite Reef Report", "greatwhite_reef_report", "Build a defensive packet-analysis report"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ])
    return rows


def install_menu_catalog() -> None:
    """Install GreatWhite Reef into the shared wrapped menu catalog."""

    from . import menu_catalog
    from .menu_catalog import _item

    if GROUP_NAME not in menu_catalog.MENU_GROUPS:
        insert_at = menu_catalog.MENU_GROUPS.index("Reports & Reviews") if "Reports & Reviews" in menu_catalog.MENU_GROUPS else len(menu_catalog.MENU_GROUPS)
        menu_catalog.MENU_GROUPS.insert(insert_at, GROUP_NAME)
        menu_catalog._GROUP_ORDER = {name: index for index, name in enumerate(menu_catalog.MENU_GROUPS)}

    if not any(str(entry.get("command", "")) == f"submenu:{SUBMENU_NAME}" for entry in menu_catalog.MAIN_MENU_ITEMS):
        main_row = _item(GROUP_NAME, "GreatWhite Reef", f"submenu:{SUBMENU_NAME}", "Open TigerShark and Great Wire Shark packet-analysis tools")
        insert_at = next((idx for idx, entry in enumerate(menu_catalog.MAIN_MENU_ITEMS) if str(entry.get("command", "")) == "submenu:reports"), len(menu_catalog.MAIN_MENU_ITEMS))
        menu_catalog.MAIN_MENU_ITEMS.insert(insert_at, main_row)

    _refresh_menu_rows()

    if not getattr(menu_catalog, "_greatwhite_reef_title_patch", False):
        original_submenu_title = menu_catalog.submenu_title

        def patched_submenu_title(menu_name: str) -> str:
            if menu_name == SUBMENU_NAME:
                return GROUP_NAME
            return original_submenu_title(menu_name)

        menu_catalog.submenu_title = patched_submenu_title
        menu_catalog._greatwhite_reef_title_patch = True

    _install_catalog_refresh_patch()
    _install_action_runner_patch()


def _refresh_menu_rows() -> None:
    from . import menu_catalog

    menu_catalog.SUBMENU_ITEMS[SUBMENU_NAME] = _menu_rows()


def _install_catalog_refresh_patch() -> None:
    from . import menu_catalog

    if getattr(menu_catalog, "_greatwhite_reef_refresh_patch", False):
        return
    original_entries_for_menu = menu_catalog._entries_for_menu

    def patched_entries_for_menu(menu_name: str = "main"):
        if menu_name == SUBMENU_NAME:
            _refresh_menu_rows()
        return original_entries_for_menu(menu_name)

    menu_catalog._entries_for_menu = patched_entries_for_menu
    menu_catalog._greatwhite_reef_refresh_patch = True


def _install_action_runner_patch() -> None:
    try:
        from . import menu_action_runner
    except Exception:
        return
    if getattr(menu_action_runner, "_greatwhite_reef_action_patch", False):
        return
    original_runner = menu_action_runner.run_automated_menu_action

    def patched_runner(command: str, label: str = "", group: str = "") -> dict[str, Any]:
        if _is_greatwhite_command(command):
            return run_greatwhite_menu_action(command, label, group)
        return original_runner(command, label, group)

    menu_action_runner.run_automated_menu_action = patched_runner
    menu_action_runner._greatwhite_reef_action_patch = True


def _now_slug() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _write_json(stem: str, payload: dict[str, Any]) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload.setdefault("updated_at", time.time())
    path = OUTPUT_DIR / f"{_now_slug()}_{stem}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    STATUS_PATH.write_text(json.dumps({"status": payload.get("status"), "command": payload.get("command"), "artifact_path": str(path), "updated_at": time.time()}, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def _write_markdown(stem: str, body: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{_now_slug()}_{stem}.md"
    path.write_text(body, encoding="utf-8")
    return str(path)


def _run(args: list[str], *, timeout: int = 20) -> dict[str, Any]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "args": args}
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "stdout": "", "stderr": f"command not found: {args[0]}", "args": args}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "returncode": 124, "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "", "stderr": f"timeout after {timeout}s", "args": args}


def _tool_path(name: str) -> str | None:
    return shutil.which(name)


def _pcap_roots() -> list[Path]:
    roots = [Path("logs")]
    extra = os.getenv("KOALABYTE_REEF_PCAP_IMPORT_DIRS", "").strip()
    if extra:
        roots.extend(Path(item) for item in extra.split(os.pathsep) if item.strip())
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve()) if root.exists() else str(root)
        if key not in seen:
            unique.append(root)
            seen.add(key)
    return unique


def _is_pcap(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".pcap", ".pcapng"}


def _target_name(source: Path) -> str:
    safe_name = "".join(ch if ch.isalnum() or ch in ".-_" else "_" for ch in source.name)
    return safe_name or f"pcap_{int(time.time())}.pcapng"


def _sync_pcaps() -> dict[str, Any]:
    PCAP_DIR.mkdir(parents=True, exist_ok=True)
    target_root = PCAP_DIR.resolve()
    imported: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for root in _pcap_roots():
        if not root.exists() or not root.is_dir():
            continue
        for source in root.rglob("*.pcap*"):
            try:
                if not _is_pcap(source):
                    continue
                resolved = source.resolve()
                if target_root in resolved.parents or resolved.parent == target_root:
                    continue
                name = _target_name(source)
                dest = PCAP_DIR / name
                if dest.exists():
                    if dest.stat().st_size == source.stat().st_size:
                        skipped.append({"source": str(source), "reason": "already synced", "target": str(dest)})
                        continue
                    dest = PCAP_DIR / f"{source.stem}_{abs(hash(str(resolved))) & 0xffff:x}{source.suffix}"
                shutil.copy2(source, dest)
                imported.append({"source": str(source), "target": str(dest)})
            except Exception as exc:
                errors.append({"source": str(source), "error": str(exc)})
    return {"imported": imported, "skipped": skipped, "errors": errors, "pcap_dir": str(PCAP_DIR)}


def _pcap_files() -> list[Path]:
    _sync_pcaps()
    PCAP_DIR.mkdir(parents=True, exist_ok=True)
    files = [path for path in PCAP_DIR.iterdir() if _is_pcap(path)]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return files[:MAX_DYNAMIC_PCAP_ROWS]


def _latest_pcap() -> Path | None:
    files = _pcap_files()
    return files[0] if files else None


def _pcap_by_name(name: str) -> Path | None:
    requested = Path(name).name
    for path in _pcap_files():
        if path.name == requested:
            return path
    return None


def _parse_interfaces(raw: str) -> list[dict[str, str]]:
    interfaces: list[dict[str, str]] = []
    for line in raw.splitlines():
        cleaned = line.strip()
        if not cleaned or "." not in cleaned:
            continue
        number, rest = cleaned.split(".", 1)
        token = rest.strip().split(" ", 1)[0].strip()
        if token:
            interfaces.append({"number": number.strip(), "name": token, "description": rest.strip()})
    return interfaces


def _interfaces() -> dict[str, Any]:
    if not _tool_path("tshark"):
        return {"status": "TIGERSHARK_MISSING", "interfaces": [], "error": "tshark is not installed"}
    result = _run(["tshark", "-D"], timeout=15)
    interfaces = _parse_interfaces(str(result.get("stdout", ""))) if result.get("ok") else []
    return {"status": "TIGERSHARK_INTERFACES_READY" if result.get("ok") else "TIGERSHARK_INTERFACES_FAILED", "interfaces": interfaces, "raw": result}


def _status() -> dict[str, Any]:
    sync = _sync_pcaps()
    files = _pcap_files()
    latest = files[0] if files else None
    payload = {
        "status": "GREATWHITE_REEF_READY" if _tool_path("tshark") else "GREATWHITE_REEF_NEEDS_TIGERSHARK",
        "command": "greatwhite_reef_status",
        "tigershark": {"binary": _tool_path("tshark"), "display_name": "TigerShark", "upstream_tool": "tshark"},
        "great_wire_shark": {"binary": _tool_path("wireshark"), "display_name": "Great Wire Shark", "upstream_tool": "wireshark"},
        "pcap_dir": str(PCAP_DIR),
        "pcap_count": len(files),
        "visible_pcap_rows": [path.name for path in files],
        "latest_pcap": str(latest) if latest else "",
        "sync": sync,
        "scope": "owned-device or written-scope lab PCAP review only",
        "wrapped_ui": True,
        "manual_shell_required": False,
    }
    payload["artifact_path"] = _write_json("status", payload)
    return payload


def _install_check() -> dict[str, Any]:
    tiger_version = _run(["tshark", "-v"], timeout=10) if _tool_path("tshark") else {"ok": False, "stderr": "tshark not installed"}
    great_wire_version = _run(["wireshark", "--version"], timeout=10) if _tool_path("wireshark") else {"ok": False, "stderr": "wireshark not installed"}
    payload = {
        "status": "TIGERSHARK_READY" if tiger_version.get("ok") else "TIGERSHARK_MISSING_OR_BLOCKED",
        "command": "greatwhite_tigershark_check",
        "tigershark_version": tiger_version,
        "great_wire_shark_version": great_wire_version,
        "install_hint": "sudo apt install -y tshark wireshark" if not tiger_version.get("ok") else "TigerShark command path is ready.",
        "wrapped_ui": True,
        "manual_shell_required": False,
    }
    payload["artifact_path"] = _write_json("install_check", payload)
    return payload


def _interfaces_action() -> dict[str, Any]:
    payload = {"command": "greatwhite_tigershark_interfaces", "wrapped_ui": True, "manual_shell_required": False, **_interfaces()}
    payload["artifact_path"] = _write_json("interfaces", payload)
    return payload


def _pcap_folder() -> dict[str, Any]:
    PCAP_DIR.mkdir(parents=True, exist_ok=True)
    sync = _sync_pcaps()
    readme = PCAP_DIR / "README.md"
    if not readme.exists():
        readme.write_text("# GreatWhite Reef PCAP Folder\n\nOwned-device or written-scope `.pcap` / `.pcapng` files are synced here for TigerShark and Great Wire Shark review.\n", encoding="utf-8")
    files = _pcap_files()
    payload = {"status": "TIGERSHARK_PCAP_FOLDER_READY", "command": "greatwhite_tigershark_pcap_folder", "pcap_dir": str(PCAP_DIR), "pcap_count": len(files), "visible_pcap_rows": [path.name for path in files], "sync": sync, "readme": str(readme), "wrapped_ui": True, "manual_shell_required": False}
    payload["artifact_path"] = _write_json("pcap_folder", payload)
    return payload


def _read_pcap(path: Path, command: str) -> dict[str, Any]:
    if not _tool_path("tshark"):
        payload = {"status": "TIGERSHARK_MISSING", "command": command, "selected_pcap": str(path), "wrapped_ui": True, "manual_shell_required": False}
        payload["artifact_path"] = _write_json("read_selected_missing", payload)
        return payload
    summary = _run(["tshark", "-r", str(path), "-q", "-z", "io,phs"], timeout=30)
    packet_preview = _run(["tshark", "-r", str(path), "-c", "20"], timeout=30)
    payload = {
        "status": "TIGERSHARK_PCAP_SUMMARY_READY" if summary.get("ok") else "TIGERSHARK_PCAP_SUMMARY_FAILED",
        "command": command,
        "selected_pcap": str(path),
        "pcap_name": path.name,
        "pcap_size_bytes": path.stat().st_size,
        "summary": summary,
        "packet_preview": packet_preview,
        "wrapped_ui": True,
        "manual_shell_required": False,
    }
    payload["artifact_path"] = _write_json("read_selected", payload)
    return payload


def _read_latest() -> dict[str, Any]:
    latest = _latest_pcap()
    if latest is None:
        payload = {"status": "TIGERSHARK_NO_LOCAL_PCAP", "command": "greatwhite_tigershark_read_latest", "pcap_dir": str(PCAP_DIR), "wrapped_ui": True, "manual_shell_required": False}
        payload["artifact_path"] = _write_json("read_latest_none", payload)
        return payload
    return _read_pcap(latest, "greatwhite_tigershark_read_latest")


def _read_selected(command: str) -> dict[str, Any]:
    requested = command.split(":", 1)[1] if ":" in command else ""
    path = _pcap_by_name(requested)
    if path is None:
        payload = {"status": "TIGERSHARK_SELECTED_PCAP_NOT_FOUND", "command": command, "requested_pcap": requested, "pcap_dir": str(PCAP_DIR), "available_pcaps": [item.name for item in _pcap_files()], "wrapped_ui": True, "manual_shell_required": False}
        payload["artifact_path"] = _write_json("read_selected_not_found", payload)
        return payload
    return _read_pcap(path, command)


def _great_wire_notes() -> dict[str, Any]:
    latest = _latest_pcap()
    body = "# Great Wire Shark Launch Notes\n\n"
    body += "Great Wire Shark is the KoalaByte name for Wireshark GUI review.\n\n"
    body += "Use it only for owned-device or written-scope lab captures.\n\n"
    if latest:
        body += f"Latest local PCAP: `{latest}`\n\n"
        body += f"Desktop review command: `wireshark {latest}`\n"
    else:
        body += f"No local PCAP exists yet. Add a `.pcap` or `.pcapng` file to `{PCAP_DIR}` first.\n"
    md_path = _write_markdown("great_wire_shark_launch_notes", body)
    payload = {"status": "GREAT_WIRE_SHARK_NOTES_READY", "command": "great_wire_shark_launch_notes", "latest_pcap": str(latest) if latest else "", "markdown_path": md_path, "wrapped_ui": True, "manual_shell_required": False}
    payload["artifact_path"] = _write_json("great_wire_shark_notes", payload)
    return payload


def _folder_notes() -> dict[str, Any]:
    sync = _sync_pcaps()
    body = "# Great Wire Shark Folder Notes\n\n"
    body += f"PCAP review folder: `{PCAP_DIR}`\n\n"
    body += "Owned-device or written-scope PCAPs found under `logs/` are synced here automatically.\n\n"
    body += "Highlight any `PCAP N: filename.pcapng` row in the GreatWhite Reef menu, then select it with buttons, touchscreen, keyboard, or voice to run TigerShark Read on that file.\n"
    md_path = _write_markdown("great_wire_shark_folder_notes", body)
    payload = {"status": "GREAT_WIRE_SHARK_FOLDER_NOTES_READY", "command": "great_wire_shark_folder_notes", "pcap_dir": str(PCAP_DIR), "sync": sync, "markdown_path": md_path, "wrapped_ui": True, "manual_shell_required": False}
    payload["artifact_path"] = _write_json("folder_notes", payload)
    return payload


def _report() -> dict[str, Any]:
    sync = _sync_pcaps()
    files = _pcap_files()
    latest = files[0] if files else None
    body = "# GreatWhite Reef Defensive Packet Analysis Report\n\n"
    body += f"Generated: {_now_slug()}\n\n"
    body += "## Scope\n\nOwned-device lab traffic or written-scope packet analysis only.\n\n"
    body += "## Wrapped Tool Names\n\n- TigerShark: KoalaByte wrapped tshark review automation\n- Great Wire Shark: KoalaByte wrapped Wireshark GUI review notes\n\n"
    body += "## PCAP Folder\n\n"
    body += f"`{PCAP_DIR}`\n\n"
    body += "## Current Files\n\n"
    if files:
        for index, path in enumerate(files, start=1):
            body += f"- PCAP {index}: `{path.name}` ({path.stat().st_size} bytes)\n"
    else:
        body += f"- No PCAP found in `{PCAP_DIR}` yet.\n"
    md_path = _write_markdown("greatwhite_reef_report", body)
    payload = {"status": "GREATWHITE_REEF_REPORT_READY", "command": "greatwhite_reef_report", "markdown_path": md_path, "latest_pcap": str(latest) if latest else "", "pcap_count": len(files), "sync": sync, "wrapped_ui": True, "manual_shell_required": False}
    payload["artifact_path"] = _write_json("report", payload)
    return payload


def run_greatwhite_menu_action(command: str, label: str = "", group: str = "") -> dict[str, Any]:
    handlers: dict[str, Callable[[], dict[str, Any]]] = {
        "greatwhite_reef_status": _status,
        "greatwhite_tigershark_check": _install_check,
        "greatwhite_tigershark_interfaces": _interfaces_action,
        "greatwhite_tigershark_pcap_folder": _pcap_folder,
        "greatwhite_tigershark_read_latest": _read_latest,
        "great_wire_shark_launch_notes": _great_wire_notes,
        "great_wire_shark_folder_notes": _folder_notes,
        "greatwhite_reef_report": _report,
    }
    if command.startswith("greatwhite_pcap_read:"):
        handler = lambda: _read_selected(command)
    else:
        handler = handlers.get(command)
    if handler is None:
        payload = {"status": "GREATWHITE_REEF_UNKNOWN_ACTION", "command": command, "label": label, "group": group, "wrapped_ui": True, "manual_shell_required": False}
        payload["artifact_path"] = _write_json("unknown_action", payload)
        return payload
    try:
        payload = handler()
        payload.setdefault("label", label)
        payload.setdefault("group", group)
        payload.setdefault("voice_command_compatible", True)
        return payload
    except Exception as exc:
        payload = {"status": "GREATWHITE_REEF_ACTION_FAILED", "command": command, "label": label, "group": group, "error": str(exc), "wrapped_ui": True, "manual_shell_required": False}
        payload["artifact_path"] = _write_json("action_failed", payload)
        return payload
