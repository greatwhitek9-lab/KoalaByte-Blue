#!/usr/bin/env python3
"""Guarded SD-card formatter for KoalaByte Blue.

This module is intentionally conservative. It is designed for formatting a
secondary/removable SD card attached through a USB reader, not the live
Raspberry Pi boot card. Actual formatting requires an explicit device path and
an exact confirmation phrase.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional

ACTION_NAME = "SD Card Formatter"
COMMAND = "sd_card_formatter"
CONFIRM_PHRASE = "ERASE-KOALABYTE-SD"
DEFAULT_LABEL = "KOALABYTE"
SUPPORTED_FILESYSTEMS = {"fat32", "exfat"}
LOG_DIR = Path("logs/sd_card_formatter")
REMOVABLE_TRANSPORTS = {"usb", "sd"}


@dataclass
class BlockDevice:
    name: str
    path: str
    size: str = ""
    device_type: str = ""
    tran: Optional[str] = None
    hotplug: bool = False
    removable: bool = False
    model: Optional[str] = None
    mountpoints: list[str] = field(default_factory=list)
    fstype: Optional[str] = None
    children: list["BlockDevice"] = field(default_factory=list)

    @classmethod
    def from_lsblk(cls, data: dict[str, Any]) -> "BlockDevice":
        raw_mounts = data.get("mountpoints")
        mounts: list[str]
        if isinstance(raw_mounts, list):
            mounts = [str(item) for item in raw_mounts if item]
        elif raw_mounts:
            mounts = [str(raw_mounts)]
        else:
            mounts = []
        return cls(
            name=str(data.get("name", "")),
            path=str(data.get("path", "")),
            size=str(data.get("size", "")),
            device_type=str(data.get("type", "")),
            tran=data.get("tran"),
            hotplug=_truthy(data.get("hotplug")),
            removable=_truthy(data.get("rm")),
            model=data.get("model"),
            mountpoints=mounts,
            fstype=data.get("fstype"),
            children=[cls.from_lsblk(child) for child in data.get("children", []) or []],
        )

    def all_mountpoints(self) -> list[str]:
        mounts = list(self.mountpoints)
        for child in self.children:
            mounts.extend(child.all_mountpoints())
        return mounts

    def partition_paths(self) -> list[str]:
        return [child.path for child in self.children if child.path]

    def looks_removable(self) -> bool:
        return self.removable or self.hotplug or self.tran in REMOVABLE_TRANSPORTS


@dataclass
class FormatResult:
    action: str
    device: Optional[str]
    filesystem: str
    label: str
    dry_run: bool
    status: str
    warning: str
    commands: list[list[str]]
    output: list[str] = field(default_factory=list)
    safety: dict[str, Any] = field(default_factory=dict)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def _require_tool(tool: str) -> None:
    if shutil.which(tool) is None:
        raise RuntimeError(f"required tool not found: {tool}")


def _lsblk_json() -> dict[str, Any]:
    _require_tool("lsblk")
    result = _run(["lsblk", "--json", "-o", "NAME,PATH,SIZE,TYPE,TRAN,HOTPLUG,RM,MODEL,MOUNTPOINTS,FSTYPE"], check=True)
    return json.loads(result.stdout or "{}")


def list_block_devices() -> list[BlockDevice]:
    data = _lsblk_json()
    return [BlockDevice.from_lsblk(item) for item in data.get("blockdevices", [])]


def find_device(device_path: str) -> BlockDevice:
    for device in list_block_devices():
        if device.path == device_path:
            return device
    raise RuntimeError(f"device not found by lsblk: {device_path}")


def _root_source() -> str:
    try:
        result = _run(["findmnt", "-n", "-o", "SOURCE", "/"], check=True)
        return result.stdout.strip()
    except Exception:
        return ""


def _looks_like_whole_disk(path: str) -> bool:
    return bool(re.fullmatch(r"/dev/(sd[a-z]|mmcblk\d+|usb[a-z]|vd[a-z])", path))


def _partition_path(device_path: str, partition_number: int = 1) -> str:
    if re.fullmatch(r"/dev/mmcblk\d+", device_path):
        return f"{device_path}p{partition_number}"
    return f"{device_path}{partition_number}"


def _device_is_parent_of_root(device_path: str, root_source: str) -> bool:
    if not root_source:
        return False
    if root_source == device_path:
        return True
    if device_path.startswith("/dev/mmcblk"):
        return root_source.startswith(f"{device_path}p")
    return root_source.startswith(device_path)


def _validate_label(label: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", label.strip().upper())[:11]
    if not safe:
        safe = DEFAULT_LABEL
    return safe


def _validate_filesystem(filesystem: str) -> str:
    fs = filesystem.strip().lower()
    if fs not in SUPPORTED_FILESYSTEMS:
        raise RuntimeError(f"unsupported filesystem: {filesystem}; choose one of {sorted(SUPPORTED_FILESYSTEMS)}")
    return fs


def _build_commands(device_path: str, filesystem: str, label: str, *, unmount: bool) -> list[list[str]]:
    filesystem = _validate_filesystem(filesystem)
    label = _validate_label(label)
    partition = _partition_path(device_path, 1)

    commands: list[list[str]] = []
    if unmount:
        commands.append(["sudo", "umount", f"{device_path}*"])
    commands.extend(
        [
            ["sudo", "wipefs", "--all", device_path],
            ["sudo", "parted", "-s", device_path, "mklabel", "msdos"],
            ["sudo", "parted", "-s", device_path, "mkpart", "primary", filesystem if filesystem == "fat32" else "fat32", "1MiB", "100%"],
            ["sudo", "partprobe", device_path],
            ["sudo", "udevadm", "settle"],
        ]
    )
    if filesystem == "fat32":
        commands.append(["sudo", "mkfs.vfat", "-F", "32", "-n", label, partition])
    else:
        commands.append(["sudo", "mkfs.exfat", "-n", label, partition])
    commands.append(["sync"])
    return commands


def make_format_plan(
    device_path: str,
    *,
    filesystem: str = "fat32",
    label: str = DEFAULT_LABEL,
    unmount: bool = False,
    allow_non_removable: bool = False,
) -> FormatResult:
    filesystem = _validate_filesystem(filesystem)
    label = _validate_label(label)

    device = find_device(device_path)
    root_source = _root_source()
    mounts = device.all_mountpoints()
    safety = {
        "destructive": True,
        "requires_explicit_device": True,
        "requires_confirmation_phrase": CONFIRM_PHRASE,
        "refuses_live_root_device": True,
        "refuses_non_removable_by_default": True,
        "root_source": root_source,
        "detected_mountpoints": mounts,
        "device_type": device.device_type,
        "transport": device.tran,
        "hotplug": device.hotplug,
        "removable": device.removable,
        "looks_removable": device.looks_removable(),
        "model": device.model,
    }

    if not _looks_like_whole_disk(device_path):
        raise RuntimeError("device must be a whole-disk path such as /dev/sda or /dev/mmcblk1, not a partition path")
    if device.device_type != "disk":
        raise RuntimeError(f"refusing non-disk device type: {device.device_type}")
    if _device_is_parent_of_root(device_path, root_source):
        raise RuntimeError(f"refusing to format the live root/boot device: {device_path}")
    if not device.looks_removable() and not allow_non_removable:
        raise RuntimeError("target does not look removable; rerun only with --allow-non-removable after physically verifying the disk")
    if mounts and not unmount:
        raise RuntimeError(f"device has mounted partitions {mounts}; rerun with --unmount after confirming it is not the live Pi SD card")

    return FormatResult(
        action=ACTION_NAME,
        device=device_path,
        filesystem=filesystem,
        label=label,
        dry_run=True,
        status="planned",
        warning="DRY RUN ONLY. No data will be erased unless the format command is run with the exact confirmation phrase.",
        commands=_build_commands(device_path, filesystem, label, unmount=unmount),
        safety=safety,
    )


def format_sd_card(
    device_path: str,
    *,
    filesystem: str = "fat32",
    label: str = DEFAULT_LABEL,
    confirm: str = "",
    unmount: bool = False,
    allow_non_removable: bool = False,
    dry_run: bool = True,
) -> FormatResult:
    plan = make_format_plan(
        device_path,
        filesystem=filesystem,
        label=label,
        unmount=unmount,
        allow_non_removable=allow_non_removable,
    )
    plan.dry_run = dry_run
    if dry_run:
        return plan

    if confirm != CONFIRM_PHRASE:
        raise RuntimeError(f"refusing to format without exact confirmation phrase: {CONFIRM_PHRASE}")
    if os.geteuid() != 0:
        raise RuntimeError("actual formatting must be run as root; dry-run planning does not require root")

    _require_tool("wipefs")
    _require_tool("parted")
    _require_tool("partprobe")
    _require_tool("udevadm")
    if plan.filesystem == "fat32":
        _require_tool("mkfs.vfat")
    else:
        _require_tool("mkfs.exfat")

    output: list[str] = []
    for command in plan.commands:
        if command[:2] == ["sudo", "umount"]:
            # Expand simple whole-disk partition glob safely in Python rather than shell.
            partitions = find_device(device_path).partition_paths()
            for partition in partitions:
                result = _run(["umount", partition], check=False)
                output.append(f"$ umount {partition}\n{result.stdout}{result.stderr}".strip())
            continue
        actual = command[1:] if command and command[0] == "sudo" else command
        result = _run(actual, check=True)
        output.append(f"$ {' '.join(actual)}\n{result.stdout}{result.stderr}".strip())

    plan.status = "formatted"
    plan.warning = "Formatting complete. Safely eject/unplug the card after sync returns."
    plan.output = output
    _write_log(plan)
    return plan


def _write_log(result: FormatResult) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "last_format_result.json"
    path.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")


def _print_devices(devices: Iterable[BlockDevice], *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps([asdict(device) for device in devices], indent=2, sort_keys=True))
        return
    print("KoalaByte Blue SD Card Formatter - detected block devices")
    print("Use a secondary/removable SD card in a USB reader. Do not format the live Pi boot card.")
    for device in devices:
        removable = "removable" if device.looks_removable() else "internal/unknown"
        mounts = ",".join(device.all_mountpoints()) or "-"
        print(f"- {device.path:12} {device.size:>8} {device.device_type:>5} {removable:>16} model={device.model or '-'} mounts={mounts}")


def _print_result(result: FormatResult, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return
    print(f"{result.action}: {result.status}")
    print(result.warning)
    print(f"Device: {result.device}")
    print(f"Filesystem: {result.filesystem}")
    print(f"Label: {result.label}")
    print("Commands:")
    for command in result.commands:
        print("  " + " ".join(command))


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue guarded SD-card formatter")
    sub = parser.add_subparsers(dest="command")

    list_parser = sub.add_parser("list", help="List detected block devices")
    list_parser.add_argument("--json", action="store_true", help="Print JSON")

    plan_parser = sub.add_parser("plan", help="Show a dry-run format plan")
    plan_parser.add_argument("--device", required=True, help="Whole disk device, for example /dev/sda or /dev/mmcblk1")
    plan_parser.add_argument("--fs", default="fat32", choices=sorted(SUPPORTED_FILESYSTEMS), help="Filesystem to create")
    plan_parser.add_argument("--label", default=DEFAULT_LABEL, help="Volume label")
    plan_parser.add_argument("--unmount", action="store_true", help="Allow mounted partitions to be unmounted during the real format")
    plan_parser.add_argument("--allow-non-removable", action="store_true", help="Permit a disk that does not report itself as removable after manual verification")
    plan_parser.add_argument("--json", action="store_true", help="Print JSON")

    fmt_parser = sub.add_parser("format", help="Erase and format an SD card after explicit confirmation")
    fmt_parser.add_argument("--device", required=True, help="Whole disk device, for example /dev/sda or /dev/mmcblk1")
    fmt_parser.add_argument("--fs", default="fat32", choices=sorted(SUPPORTED_FILESYSTEMS), help="Filesystem to create")
    fmt_parser.add_argument("--label", default=DEFAULT_LABEL, help="Volume label")
    fmt_parser.add_argument("--unmount", action="store_true", help="Unmount mounted partitions before formatting")
    fmt_parser.add_argument("--allow-non-removable", action="store_true", help="Permit a disk that does not report itself as removable after manual verification")
    fmt_parser.add_argument("--confirm", default="", help=f"Required exact phrase: {CONFIRM_PHRASE}")
    fmt_parser.add_argument("--json", action="store_true", help="Print JSON")

    args = parser.parse_args(argv)
    command = args.command or "list"
    try:
        if command == "list":
            _print_devices(list_block_devices(), as_json=getattr(args, "json", False))
            return 0
        if command == "plan":
            result = make_format_plan(
                args.device,
                filesystem=args.fs,
                label=args.label,
                unmount=args.unmount,
                allow_non_removable=args.allow_non_removable,
            )
            _print_result(result, as_json=args.json)
            return 0
        if command == "format":
            result = format_sd_card(
                args.device,
                filesystem=args.fs,
                label=args.label,
                confirm=args.confirm,
                unmount=args.unmount,
                allow_non_removable=args.allow_non_removable,
                dry_run=False,
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
