from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_OUTPUT_DIR = Path("logs/koala_bluez")


@dataclass(frozen=True)
class BluezToolSpec:
    koala_name: str
    command: str
    purpose: str
    safe_default: bool = True
    target_required: bool = False
    owned_device_required: bool = False


BLUEZ_TOOLS: List[BluezToolSpec] = [
    BluezToolSpec("Koala Blue Controller", "bluetoothctl", "Adapter power, discovery, local controller status"),
    BluezToolSpec("Koala Blue Manager", "btmgmt", "Local controller management/status"),
    BluezToolSpec("Koala Blue Monitor", "btmon", "Local HCI monitor capture/logging"),
    BluezToolSpec("Koala Blue Radio List", "hciconfig", "Local adapter identity/status"),
    BluezToolSpec("Koala Blue Classic List", "hcitool", "Legacy local inquiry/LE scan support when installed"),
    BluezToolSpec("Koala Blue Blocker Status", "rfkill", "Local Bluetooth soft/hard block status"),
    BluezToolSpec("Koala Blue RFCOMM Status", "rfcomm", "Local RFCOMM binding/status"),
    BluezToolSpec("Koala Blue Service Notes", "sdptool", "Owned-device service browsing when explicitly targeted", target_required=True, owned_device_required=True),
    BluezToolSpec("Koala Blue Link Echo", "l2ping", "Owned-device link echo when explicitly targeted", target_required=True, owned_device_required=True),
    BluezToolSpec("Koala Blue GATT Notes", "gatttool", "Legacy owned-device GATT observation when installed", target_required=True, owned_device_required=True),
]


@dataclass
class CommandResult:
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    skipped: bool = False
    reason: Optional[str] = None


@dataclass
class BluezRunResult:
    action: str
    started_at: float
    ended_at: float
    output_dir: str
    results: List[CommandResult] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _run(command: List[str], timeout_seconds: int = 15) -> CommandResult:
    binary = command[0]
    if shutil.which(binary) is None:
        return CommandResult(command=command, returncode=127, stdout="", stderr="", skipped=True, reason=f"{binary} not installed")
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        return CommandResult(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(command=command, returncode=124, stdout=exc.stdout or "", stderr=exc.stderr or "timeout", skipped=False, reason="timeout")


def inventory(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    results: List[CommandResult] = []
    for spec in BLUEZ_TOOLS:
        path = shutil.which(spec.command)
        results.append(CommandResult(
            command=[spec.command],
            returncode=0 if path else 127,
            stdout=path or "",
            stderr="",
            skipped=path is None,
            reason=None if path else "not installed",
        ))
    ended = time.time()
    out = output_dir / "koala_bluez_inventory.json"
    payload = BluezRunResult("inventory", started, ended, str(output_dir), results, {"inventory": str(out)})
    _write_json(out, asdict(payload))
    return payload


def status(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    commands = [
        ["bluetoothctl", "list"],
        ["bluetoothctl", "show"],
        ["btmgmt", "info"],
        ["rfkill", "list", "bluetooth"],
        ["hciconfig", "-a"],
        ["rfcomm", "-a"],
    ]
    results = [_run(cmd, timeout_seconds=12) for cmd in commands]
    ended = time.time()
    out = output_dir / f"koala_bluez_status_{int(started)}.json"
    payload = BluezRunResult("status", started, ended, str(output_dir), results, {"status": str(out)})
    _write_json(out, asdict(payload))
    return payload


def scan(duration_seconds: int = 15, output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    duration_seconds = max(3, min(duration_seconds, 120))
    results: List[CommandResult] = []
    results.append(_run(["bluetoothctl", "power", "on"], timeout_seconds=10))
    results.append(_run(["bluetoothctl", "--timeout", str(duration_seconds), "scan", "on"], timeout_seconds=duration_seconds + 5))
    results.append(_run(["bluetoothctl", "scan", "off"], timeout_seconds=10))
    results.append(_run(["bluetoothctl", "devices"], timeout_seconds=10))
    results.append(_run(["bluetoothctl", "devices", "Connected"], timeout_seconds=10))
    ended = time.time()
    out = output_dir / f"koala_bluez_scan_{int(started)}.json"
    payload = BluezRunResult("scan", started, ended, str(output_dir), results, {"scan": str(out)})
    _write_json(out, asdict(payload))
    return payload


def monitor(duration_seconds: int = 20, output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    duration_seconds = max(5, min(duration_seconds, 300))
    raw_log = output_dir / f"koala_bluez_btmon_{int(started)}.log"
    result = _run(["btmon"], timeout_seconds=duration_seconds)
    raw_log.write_text((result.stdout or "") + ("\n--- STDERR ---\n" + result.stderr if result.stderr else ""), encoding="utf-8")
    ended = time.time()
    out = output_dir / f"koala_bluez_monitor_{int(started)}.json"
    payload = BluezRunResult("monitor", started, ended, str(output_dir), [result], {"monitor_summary": str(out), "btmon_log": str(raw_log)})
    _write_json(out, asdict(payload))
    return payload


def info(target: str, owned_device: bool, output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    results: List[CommandResult] = []
    if not owned_device:
        results.append(CommandResult(command=["bluetoothctl", "info", target], returncode=2, stdout="", stderr="", skipped=True, reason="--owned-device is required for target-specific diagnostics"))
    else:
        results.append(_run(["bluetoothctl", "info", target], timeout_seconds=12))
    ended = time.time()
    out = output_dir / f"koala_bluez_info_{int(started)}.json"
    payload = BluezRunResult("info", started, ended, str(output_dir), results, {"info": str(out)})
    _write_json(out, asdict(payload))
    return payload


def services(target: str, owned_device: bool, output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    results: List[CommandResult] = []
    if not owned_device:
        results.append(CommandResult(command=["sdptool", "browse", target], returncode=2, stdout="", stderr="", skipped=True, reason="--owned-device is required for target-specific service browsing"))
    else:
        results.append(_run(["sdptool", "browse", target], timeout_seconds=25))
    ended = time.time()
    out = output_dir / f"koala_bluez_services_{int(started)}.json"
    payload = BluezRunResult("services", started, ended, str(output_dir), results, {"services": str(out)})
    _write_json(out, asdict(payload))
    return payload


def all_safe(duration_seconds: int = 15, output_dir: Path = DEFAULT_OUTPUT_DIR) -> List[BluezRunResult]:
    return [inventory(output_dir), status(output_dir), scan(duration_seconds, output_dir)]


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue safe BlueZ automation layer")
    parser.add_argument("action", choices=["inventory", "status", "scan", "monitor", "info", "services", "all-safe"])
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--target", default=None, help="Owned/scope-approved target address for target-specific diagnostics")
    parser.add_argument("--owned-device", action="store_true", help="Required for target-specific diagnostics")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if args.action == "inventory":
        result = inventory(output_dir)
    elif args.action == "status":
        result = status(output_dir)
    elif args.action == "scan":
        result = scan(args.duration, output_dir)
    elif args.action == "monitor":
        result = monitor(args.duration, output_dir)
    elif args.action == "info":
        if not args.target:
            parser.error("info requires --target")
        result = info(args.target, args.owned_device, output_dir)
    elif args.action == "services":
        if not args.target:
            parser.error("services requires --target")
        result = services(args.target, args.owned_device, output_dir)
    else:
        results = all_safe(args.duration, output_dir)
        print(json.dumps([asdict(item) for item in results], indent=2, sort_keys=True))
        return 0

    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
