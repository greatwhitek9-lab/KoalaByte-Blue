#!/usr/bin/env python3
"""Live boot SD maintenance for KoalaByte Blue.

A Raspberry Pi cannot safely format the SD card it is currently booted from.
This utility is for safe live-card maintenance instead: identify the live boot
source, report disk usage, and optionally clear KoalaByte-generated logs and
capture artifacts after an explicit confirmation phrase.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

ACTION_NAME = "Live Boot SD Maintenance"
COMMAND = "live_boot_sd_maintenance"
RESET_CONFIRM_PHRASE = "RESET-KOALABYTE-LIVE-SD"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_PATH = REPO_ROOT / "logs" / "boot_sd_maintenance" / "last_result.json"
SAFE_REPO_RELATIVE_TARGETS = [
    "logs",
    ".pytest_cache",
    "pi-companion/.pytest_cache",
    "pi-companion/koalablue/__pycache__",
]
OPTIONAL_ABSOLUTE_TARGETS = [
    Path("/blecaptures"),
]


@dataclass
class BootCardInfo:
    action: str
    root_source: str
    root_target: str
    root_fstype: str
    root_options: str
    parent_disk: str
    disk_size: str
    root_usage: dict[str, str]
    can_self_format: bool
    warning: str


@dataclass
class MaintenanceResult:
    action: str
    status: str
    dry_run: bool
    warning: str
    targets: list[str]
    removed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    safety: dict[str, Any] = field(default_factory=dict)


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def _safe_stdout(command: list[str]) -> str:
    try:
        return _run(command, check=True).stdout.strip()
    except Exception:
        return ""


def _root_source() -> str:
    return _safe_stdout(["findmnt", "-n", "-o", "SOURCE", "/"])


def _root_info_row() -> tuple[str, str, str, str]:
    raw = _safe_stdout(["findmnt", "-n", "-o", "SOURCE,TARGET,FSTYPE,OPTIONS", "/"])
    parts = raw.split(maxsplit=3)
    while len(parts) < 4:
        parts.append("")
    return parts[0], parts[1], parts[2], parts[3]


def _parent_disk(source: str) -> str:
    if not source:
        return ""
    parent = _safe_stdout(["lsblk", "-no", "PKNAME", source])
    if parent:
        return f"/dev/{parent}"
    if source.startswith("/dev/mmcblk") and "p" in source:
        return source.rsplit("p", 1)[0]
    if source.startswith("/dev/sd"):
        return source.rstrip("0123456789")
    return source


def _disk_size(device: str) -> str:
    if not device:
        return ""
    return _safe_stdout(["lsblk", "-dn", "-o", "SIZE", device])


def _usage(path: Path) -> dict[str, str]:
    try:
        usage = shutil.disk_usage(path)
        return {
            "total": str(usage.total),
            "used": str(usage.used),
            "free": str(usage.free),
            "total_human": _human_bytes(usage.total),
            "used_human": _human_bytes(usage.used),
            "free_human": _human_bytes(usage.free),
        }
    except Exception as exc:
        return {"error": str(exc)}


def _human_bytes(value: int) -> str:
    amount = float(value)
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if amount < 1024.0 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024.0
    return f"{value} B"


def boot_card_info() -> BootCardInfo:
    source, target, fstype, options = _root_info_row()
    disk = _parent_disk(source)
    return BootCardInfo(
        action=ACTION_NAME,
        root_source=source,
        root_target=target or "/",
        root_fstype=fstype,
        root_options=options,
        parent_disk=disk,
        disk_size=_disk_size(disk),
        root_usage=_usage(Path("/")),
        can_self_format=False,
        warning="The live boot SD card cannot be safely formatted while KoalaByte Blue is running from it. Use Raspberry Pi Imager or another computer to reformat/reimage the boot card.",
    )


def _safe_targets(include_captures: bool) -> list[Path]:
    targets = [(REPO_ROOT / rel).resolve() for rel in SAFE_REPO_RELATIVE_TARGETS]
    if include_captures:
        targets.extend(path for path in OPTIONAL_ABSOLUTE_TARGETS)
    return targets


def _is_safe_target(path: Path) -> bool:
    resolved = path.resolve()
    repo_root = REPO_ROOT.resolve()
    if resolved == repo_root:
        return False
    if str(resolved).startswith(str(repo_root) + os.sep):
        return True
    if resolved == Path("/blecaptures"):
        return True
    return False


def reset_koalabyte_data(*, confirm: str = "", include_captures: bool = False, dry_run: bool = True) -> MaintenanceResult:
    targets = _safe_targets(include_captures)
    result = MaintenanceResult(
        action=ACTION_NAME,
        status="planned" if dry_run else "reset",
        dry_run=dry_run,
        warning="Dry run only. No files removed." if dry_run else "KoalaByte-generated live-card data reset complete. Reboot recommended.",
        targets=[str(path) for path in targets],
        safety={
            "formats_live_boot_card": False,
            "removes_operating_system": False,
            "requires_confirmation_phrase": RESET_CONFIRM_PHRASE,
            "repo_root": str(REPO_ROOT),
            "include_blecaptures": include_captures,
        },
    )
    if dry_run:
        result.skipped = [str(path) for path in targets if not path.exists()]
        return result
    if confirm != RESET_CONFIRM_PHRASE:
        raise RuntimeError(f"refusing live-card data reset without exact confirmation phrase: {RESET_CONFIRM_PHRASE}")

    for path in targets:
        if not _is_safe_target(path):
            result.skipped.append(f"unsafe target refused: {path}")
            continue
        if not path.exists():
            result.skipped.append(str(path))
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        result.removed.append(str(path))

    _write_log(result)
    return result


def _write_log(result: MaintenanceResult) -> None:
    DEFAULT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_LOG_PATH.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")


def _print_json(data: Any) -> None:
    print(json.dumps(asdict(data) if hasattr(data, "__dataclass_fields__") else data, indent=2, sort_keys=True))


def _print_status(info: BootCardInfo) -> None:
    print(f"{info.action}")
    print(info.warning)
    print(f"Root source: {info.root_source}")
    print(f"Parent disk: {info.parent_disk or '-'}")
    print(f"Disk size: {info.disk_size or '-'}")
    print(f"Filesystem: {info.root_fstype or '-'}")
    print(f"Used/free: {info.root_usage.get('used_human', '-')} used / {info.root_usage.get('free_human', '-')} free")
    print("Self-format supported: no")


def _print_result(result: MaintenanceResult, *, as_json: bool = False) -> None:
    if as_json:
        _print_json(result)
        return
    print(f"{result.action}: {result.status}")
    print(result.warning)
    print("Targets:")
    for target in result.targets:
        print(f"- {target}")
    if result.removed:
        print("Removed:")
        for item in result.removed:
            print(f"- {item}")
    if result.skipped:
        print("Skipped/missing:")
        for item in result.skipped:
            print(f"- {item}")


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue live boot SD maintenance")
    sub = parser.add_subparsers(dest="command")

    status_parser = sub.add_parser("status", help="Show live boot SD card information")
    status_parser.add_argument("--json", action="store_true", help="Print JSON")

    reset_parser = sub.add_parser("reset-data", help="Clear KoalaByte-generated logs/cache data on the live boot SD card")
    reset_parser.add_argument("--include-captures", action="store_true", help="Also remove /blecaptures if present")
    reset_parser.add_argument("--confirm", default="", help=f"Required exact phrase: {RESET_CONFIRM_PHRASE}")
    reset_parser.add_argument("--dry-run", action="store_true", help="Preview reset targets without removing files")
    reset_parser.add_argument("--json", action="store_true", help="Print JSON")

    args = parser.parse_args(argv)
    command = args.command or "status"
    try:
        if command == "status":
            info = boot_card_info()
            if args.json:
                _print_json(info)
            else:
                _print_status(info)
            return 0
        if command == "reset-data":
            dry_run = args.dry_run or args.confirm != RESET_CONFIRM_PHRASE
            result = reset_koalabyte_data(
                confirm=args.confirm,
                include_captures=args.include_captures,
                dry_run=dry_run,
            )
            _print_result(result, as_json=args.json)
            return 0
    except Exception as exc:
        if getattr(args, "json", False):
            print(json.dumps({"action": ACTION_NAME, "status": "blocked", "error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"{ACTION_NAME}: blocked - {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
