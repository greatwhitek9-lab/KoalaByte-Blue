from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import bluez_tools

DEFAULT_OUTPUT_DIR = Path("logs/t114_bluez")
DEFAULT_VALIDATION_PATH = Path("logs/hardware_validation/t114_bluez_validation.json")


@dataclass
class T114ControllerCheck:
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    skipped: bool = False
    reason: Optional[str] = None


@dataclass
class T114BluezResult:
    action: str
    status: str
    started_at: float
    ended_at: float
    output_dir: str
    hci_controller_expected: bool
    hci_controller_present: bool
    selected_adapter: str
    checks: List[T114ControllerCheck] = field(default_factory=list)
    wrapped_bluez_result: object = None
    artifacts: Dict[str, str] = field(default_factory=dict)
    safety: Dict[str, object] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)


def _run(command: List[str], timeout_seconds: int = 12) -> T114ControllerCheck:
    binary = command[0]
    if shutil.which(binary) is None:
        return T114ControllerCheck(command, 127, "", "", True, f"{binary} not installed")
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        return T114ControllerCheck(command, completed.returncode, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or "timeout"
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return T114ControllerCheck(command, 124, stdout, stderr, False, "timeout")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _jsonable_wrapped(value: object) -> object:
    if isinstance(value, list):
        return [asdict(item) if hasattr(item, "__dataclass_fields__") else item for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value


def _detect_adapter_from_bluetoothctl_list(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Controller "):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    return ""


def check_controller(adapter: str = "", output_dir: Path = DEFAULT_OUTPUT_DIR, validation_path: Path = DEFAULT_VALIDATION_PATH) -> T114BluezResult:
    started = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    checks = [
        _run(["bluetoothctl", "list"]),
        _run(["bluetoothctl", "show"] if not adapter else ["bluetoothctl", "show", adapter]),
        _run(["btmgmt", "info"]),
        _run(["rfkill", "list", "bluetooth"]),
    ]
    selected = adapter or _detect_adapter_from_bluetoothctl_list(checks[0].stdout)
    present = bool(selected) and any(check.returncode == 0 and check.stdout.strip() for check in checks[:2])
    ended = time.time()
    summary = output_dir / f"t114_bluez_controller_{int(started)}.json"
    result = T114BluezResult(
        action="controller-check",
        status="ready" if present else "missing_hci_controller",
        started_at=started,
        ended_at=ended,
        output_dir=str(output_dir),
        hci_controller_expected=True,
        hci_controller_present=present,
        selected_adapter=selected,
        checks=checks,
        artifacts={"summary": str(summary), "validation": str(validation_path)},
        safety={
            "authorized_lab_use_only": True,
            "local_hci_controller_check_only": True,
            "pairing_bypass": False,
            "spoofing": False,
            "packet_replay": False,
            "disruptive_actions": False,
        },
        next_steps=[] if present else [
            "Flash t114_hci_usb firmware with scripts/flash_nrf52840_t114_hci_usb.sh.",
            "Unplug/replug the Heltec board USB-C cable.",
            "Run: bluetoothctl list && bluetoothctl show",
        ],
    )
    _write_json(summary, asdict(result))
    _write_json(validation_path, asdict(result))
    return result


def run_wrapped_bluez(action: str, *, adapter: str = "", duration_seconds: int = 15, output_dir: Path = DEFAULT_OUTPUT_DIR, raw_addresses: bool = False) -> T114BluezResult:
    started = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    validation_path = Path("logs/hardware_validation") / f"t114_bluez_{action}_{int(started)}.json"
    controller = check_controller(adapter=adapter, output_dir=output_dir, validation_path=validation_path)
    if not controller.hci_controller_present:
        controller.action = action
        controller.status = "blocked_missing_hci_controller"
        _write_json(validation_path, asdict(controller))
        return controller

    if action == "manifest":
        wrapped = bluez_tools.module_manifest(output_dir=output_dir)
    elif action == "inventory":
        wrapped = bluez_tools.inventory(output_dir=output_dir)
    elif action == "status":
        wrapped = bluez_tools.status(output_dir=output_dir, raw_addresses=raw_addresses)
    elif action == "scan":
        wrapped = bluez_tools.scan(duration_seconds=duration_seconds, output_dir=output_dir, raw_addresses=raw_addresses)
    elif action == "monitor":
        wrapped = bluez_tools.monitor(duration_seconds=duration_seconds, output_dir=output_dir)
    elif action == "all-safe":
        wrapped = bluez_tools.all_safe(duration_seconds=duration_seconds, output_dir=output_dir, raw_addresses=raw_addresses)
    else:
        raise ValueError(f"Unsupported T114 BlueZ action: {action}")

    ended = time.time()
    summary = output_dir / f"t114_bluez_{action}_{int(started)}.json"
    result = T114BluezResult(
        action=action,
        status="success",
        started_at=started,
        ended_at=ended,
        output_dir=str(output_dir),
        hci_controller_expected=True,
        hci_controller_present=True,
        selected_adapter=controller.selected_adapter,
        checks=controller.checks,
        wrapped_bluez_result=_jsonable_wrapped(wrapped),
        artifacts={"summary": str(summary), "validation": str(validation_path)},
        safety={
            "authorized_lab_use_only": True,
            "uses_linux_bluez_host_stack": True,
            "expects_t114_hci_usb_firmware": True,
            "bounded_scan_duration_seconds": duration_seconds,
            "raw_addresses_requested": raw_addresses,
            "pairing_bypass": False,
            "spoofing": False,
            "packet_replay": False,
            "disruptive_actions": False,
        },
    )
    _write_json(summary, asdict(result))
    _write_json(validation_path, asdict(result))
    return result


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue Heltec T114 nRF52840 BlueZ HCI wrapper")
    parser.add_argument("action", nargs="?", default="status", choices=["controller-check", "manifest", "inventory", "status", "scan", "monitor", "all-safe"])
    parser.add_argument("--adapter", default="", help="Optional controller MAC from bluetoothctl list; leave blank to auto-detect first controller")
    parser.add_argument("--duration-seconds", type=int, default=15)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--raw-addresses", action="store_true", help="Keep raw device addresses in local lab artifacts instead of redacting/hashing when supported")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if args.action == "controller-check":
        result = check_controller(adapter=args.adapter, output_dir=output_dir)
    else:
        result = run_wrapped_bluez(
            args.action,
            adapter=args.adapter,
            duration_seconds=args.duration_seconds,
            output_dir=output_dir,
            raw_addresses=args.raw_addresses,
        )
    _print_json(asdict(result))
    return 0 if result.status in {"ready", "success"} else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())