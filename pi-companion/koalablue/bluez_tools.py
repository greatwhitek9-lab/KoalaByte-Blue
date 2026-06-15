from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_OUTPUT_DIR = Path("logs/koala_bluez")
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")


@dataclass(frozen=True)
class BluezToolSpec:
    koala_name: str
    command: str
    purpose: str
    safe_default: bool = True
    target_required: bool = False
    owned_device_required: bool = False


@dataclass(frozen=True)
class BluezModuleSpec:
    action: str
    theme_title: str
    backend: str
    purpose: str
    output_hint: str
    owned_device_required: bool = False
    target_required: bool = False


BLUEZ_TOOLS: List[BluezToolSpec] = [
    BluezToolSpec("Gumleaf Controller", "bluetoothctl", "Adapter power, discovery, and local controller status"),
    BluezToolSpec("Eucalyptus Manager", "btmgmt", "Local controller management/status"),
    BluezToolSpec("Billabong HCI Watcher", "btmon", "Local HCI monitor capture/logging"),
    BluezToolSpec("Outback Radio Ledger", "hciconfig", "Local adapter identity/status when installed"),
    BluezToolSpec("Classic Track Finder", "hcitool", "Legacy local inquiry/LE scan support when installed"),
    BluezToolSpec("Branch Block Check", "rfkill", "Local Bluetooth soft/hard block status"),
    BluezToolSpec("Treehouse RFCOMM Notes", "rfcomm", "Local RFCOMM binding/status"),
    BluezToolSpec(
        "Joey Service Notes",
        "sdptool",
        "Owned-device service browsing when explicitly targeted",
        target_required=True,
        owned_device_required=True,
    ),
    BluezToolSpec(
        "Pouch Link Echo",
        "l2ping",
        "Owned-device link echo when explicitly targeted",
        target_required=True,
        owned_device_required=True,
    ),
    BluezToolSpec(
        "Gumnut GATT Notes",
        "gatttool",
        "Legacy owned-device GATT observation when installed",
        target_required=True,
        owned_device_required=True,
    ),
    BluezToolSpec("Eucalyptus D-Bus Scout", "busctl", "Optional D-Bus Adapter1 introspection when installed"),
]


BLUEZ_MODULES: List[BluezModuleSpec] = [
    BluezModuleSpec("inventory", "Gumleaf Gear Check", "PATH inventory", "List local BlueZ helper availability under KoalaByte themed names.", "koala_bluez_inventory.json"),
    BluezModuleSpec("status", "Eucalyptus Bus Scout", "bluetoothctl/btmgmt/rfkill/busctl", "Collect local Bluetooth controller, rfkill, and optional D-Bus adapter status.", "koala_bluez_status_<timestamp>.json"),
    BluezModuleSpec("scan", "Dropbear Discovery Sweep", "bluetoothctl timed discovery", "Run a bounded discovery sweep and save redacted results by default.", "koala_bluez_scan_<timestamp>.json"),
    BluezModuleSpec("monitor", "Billabong HCI Watch", "btmon capture", "Run a bounded local HCI monitor capture for lab debugging.", "koala_bluez_btmon_<timestamp>.btsnoop"),
    BluezModuleSpec("info", "Joey Target Card", "bluetoothctl info", "Show target information only when the operator marks it as owned/in-scope.", "koala_bluez_info_<timestamp>.json", owned_device_required=True, target_required=True),
    BluezModuleSpec("services", "Treehouse Service Notes", "sdptool browse", "Browse services only for an explicitly owned/in-scope target.", "koala_bluez_services_<timestamp>.json", owned_device_required=True, target_required=True),
    BluezModuleSpec("gatt-readiness", "Gumnut GATT Readiness", "checklist artifact", "Write an owned-device GATT review checklist without performing GATT writes.", "koala_bluez_gatt_readiness_<timestamp>.json", owned_device_required=True, target_required=True),
    BluezModuleSpec("all-safe", "Kookaburra Safe Nest Run", "module sequence", "Run inventory, status, and a bounded discovery sweep using safe defaults.", "multiple artifacts"),
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
    theme_title: str
    started_at: float
    ended_at: float
    output_dir: str
    results: List[CommandResult] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    safety: Dict[str, object] = field(default_factory=dict)


def _module_title(action: str) -> str:
    for spec in BLUEZ_MODULES:
        if spec.action == action:
            return spec.theme_title
    return action


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _hash_address(address: str) -> str:
    digest = hashlib.sha256(address.upper().encode("utf-8")).hexdigest()[:12]
    return f"BT-HASH-{digest}"


def redact_addresses(text: str, raw_addresses: bool = False) -> str:
    if raw_addresses:
        return text
    return MAC_RE.sub(lambda match: _hash_address(match.group(0)), text)


def _redact_result(result: CommandResult, raw_addresses: bool = False) -> CommandResult:
    if raw_addresses:
        return result
    return CommandResult(
        command=result.command,
        returncode=result.returncode,
        stdout=redact_addresses(result.stdout, raw_addresses=False),
        stderr=redact_addresses(result.stderr, raw_addresses=False),
        skipped=result.skipped,
        reason=result.reason,
    )


def _run(command: List[str], timeout_seconds: int = 15, raw_addresses: bool = False) -> CommandResult:
    binary = command[0]
    if shutil.which(binary) is None:
        return CommandResult(command=command, returncode=127, stdout="", stderr="", skipped=True, reason=f"{binary} not installed")
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        return _redact_result(
            CommandResult(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr),
            raw_addresses=raw_addresses,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or "timeout"
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return _redact_result(
            CommandResult(command=command, returncode=124, stdout=stdout, stderr=stderr, skipped=False, reason="timeout"),
            raw_addresses=raw_addresses,
        )


def _base_safety(raw_addresses: bool, owned_device: bool = False) -> Dict[str, object]:
    return {
        "authorized_lab_use_only": True,
        "raw_addresses_requested": raw_addresses,
        "addresses_redacted_or_hashed": not raw_addresses,
        "owned_device_confirmed": owned_device,
        "pairing_bypass": False,
        "spoofing": False,
        "packet_replay": False,
        "disruptive_actions": False,
    }


def module_manifest(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    out = output_dir / "koala_bluez_module_manifest.json"
    tools = [asdict(tool) for tool in BLUEZ_TOOLS]
    modules = [asdict(module) for module in BLUEZ_MODULES]
    ended = time.time()
    payload = BluezRunResult(
        "manifest",
        "KoalaByte Blue Outback Module Deck",
        started,
        ended,
        str(output_dir),
        [],
        {"manifest": str(out)},
        _base_safety(raw_addresses=False),
    )
    _write_json(out, {"tools": tools, "modules": modules, "run": asdict(payload)})
    return payload


def inventory(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    results: List[CommandResult] = []
    for spec in BLUEZ_TOOLS:
        path = shutil.which(spec.command)
        results.append(
            CommandResult(
                command=[spec.command],
                returncode=0 if path else 127,
                stdout=path or "",
                stderr="",
                skipped=path is None,
                reason=None if path else "not installed",
            )
        )
    ended = time.time()
    out = output_dir / "koala_bluez_inventory.json"
    manifest = output_dir / "koala_bluez_module_manifest.json"
    payload = BluezRunResult(
        "inventory",
        _module_title("inventory"),
        started,
        ended,
        str(output_dir),
        results,
        {"inventory": str(out), "module_manifest": str(manifest)},
        _base_safety(raw_addresses=False),
    )
    _write_json(out, asdict(payload))
    _write_json(manifest, {"tools": [asdict(tool) for tool in BLUEZ_TOOLS], "modules": [asdict(module) for module in BLUEZ_MODULES]})
    return payload


def status(output_dir: Path = DEFAULT_OUTPUT_DIR, raw_addresses: bool = False) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    commands = [
        ["bluetoothctl", "list"],
        ["bluetoothctl", "show"],
        ["btmgmt", "info"],
        ["rfkill", "list", "bluetooth"],
        ["hciconfig", "-a"],
        ["rfcomm", "-a"],
        ["busctl", "introspect", "org.bluez", "/org/bluez/hci0", "org.bluez.Adapter1"],
    ]
    results = [_run(cmd, timeout_seconds=12, raw_addresses=raw_addresses) for cmd in commands]
    ended = time.time()
    out = output_dir / f"koala_bluez_status_{int(started)}.json"
    payload = BluezRunResult(
        "status",
        _module_title("status"),
        started,
        ended,
        str(output_dir),
        results,
        {"status": str(out)},
        _base_safety(raw_addresses=raw_addresses),
    )
    _write_json(out, asdict(payload))
    return payload


def scan(duration_seconds: int = 15, output_dir: Path = DEFAULT_OUTPUT_DIR, raw_addresses: bool = False) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    duration_seconds = max(3, min(duration_seconds, 120))
    results: List[CommandResult] = []
    results.append(_run(["bluetoothctl", "power", "on"], timeout_seconds=10, raw_addresses=raw_addresses))
    results.append(_run(["bluetoothctl", "--timeout", str(duration_seconds), "scan", "on"], timeout_seconds=duration_seconds + 8, raw_addresses=raw_addresses))
    results.append(_run(["bluetoothctl", "scan", "off"], timeout_seconds=10, raw_addresses=raw_addresses))
    results.append(_run(["bluetoothctl", "devices"], timeout_seconds=10, raw_addresses=raw_addresses))
    results.append(_run(["bluetoothctl", "devices", "Connected"], timeout_seconds=10, raw_addresses=raw_addresses))
    ended = time.time()
    out = output_dir / f"koala_bluez_scan_{int(started)}.json"
    payload = BluezRunResult(
        "scan",
        _module_title("scan"),
        started,
        ended,
        str(output_dir),
        results,
        {"scan": str(out)},
        _base_safety(raw_addresses=raw_addresses),
    )
    _write_json(out, asdict(payload))
    return payload


def monitor(duration_seconds: int = 20, output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    started = time.time()
    output_dir = _ensure_output_dir(output_dir)
    duration_seconds = max(5, min(duration_seconds, 300))
    btsnoop_log = output_dir / f"koala_bluez_btmon_{int(started)}.btsnoop"
    text_log = output_dir / f"koala_bluez_btmon_{int(started)}.log"

    if shutil.which("btmon") is None:
        result = CommandResult(command=["btmon", "-w", str(btsnoop_log)], returncode=127, stdout="", stderr="", skipped=True, reason="btmon not installed")
    else:
        command = ["btmon", "-w", str(btsnoop_log)]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=duration_seconds, check=False)
            result = CommandResult(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or "timeout"
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            result = CommandResult(command=command, returncode=124, stdout=stdout, stderr=stderr, skipped=False, reason="timeout")

    text_log.write_text((result.stdout or "") + ("\n--- STDERR ---\n" + result.stderr if result.stderr else ""), encoding="utf-8")
    ended = time.time()
    out = output_dir / f"koala_bluez_monitor_{int(started)}.json"
    artifacts = {"monitor_summary": str(out), "btmon_text_log": str(text_log)}
    if btsnoop_log.exists():
        artifacts["btmon_btsnoop"] = str(btsnoop_log)
    payload = BluezRunResult(
        "monitor",
        _module_title("monitor"),
        started,
        ended,
        str(output_dir),
        [result],
        artifacts,
        _base_safety(raw_addresses=False),
    )
    _write_json(out, asdict(payload))
    return payload


def _require_owned_target(action: str, target: Optional[str], owned_device: bool, output_dir: Path) -> Optional[BluezRunResult]:
    if target and owned_device:
        return None

    started = time.time()
    reason = "target-specific diagnostics require --target and --owned-device"
    command = [action]
    if target:
        command.append(target)
    result = CommandResult(command=command, returncode=2, stdout="", stderr="", skipped=True, reason=reason)
    ended = time.time()
    out = output_dir / f"koala_bluez_{action.replace('-', '_')}_{int(started)}.json"
    payload = BluezRunResult(
        action,
        _module_title(action),
        started,
        ended,
        str(output_dir),
        [result],
        {"blocked_summary": str(out)},
        _base_safety(raw_addresses=False, owned_device=owned_device),
    )
    _write_json(out, asdict(payload))
    return payload


def info(target: str, owned_device: bool, output_dir: Path = DEFAULT_OUTPUT_DIR, raw_addresses: bool = False) -> BluezRunResult:
    output_dir = _ensure_output_dir(output_dir)
    blocked = _require_owned_target("info", target, owned_device, output_dir)
    if blocked:
        return blocked

    started = time.time()
    results = [_run(["bluetoothctl", "info", target], timeout_seconds=12, raw_addresses=raw_addresses)]
    ended = time.time()
    out = output_dir / f"koala_bluez_info_{int(started)}.json"
    payload = BluezRunResult(
        "info",
        _module_title("info"),
        started,
        ended,
        str(output_dir),
        results,
        {"info": str(out)},
        _base_safety(raw_addresses=raw_addresses, owned_device=owned_device),
    )
    _write_json(out, asdict(payload))
    return payload


def services(target: str, owned_device: bool, output_dir: Path = DEFAULT_OUTPUT_DIR, raw_addresses: bool = False) -> BluezRunResult:
    output_dir = _ensure_output_dir(output_dir)
    blocked = _require_owned_target("services", target, owned_device, output_dir)
    if blocked:
        return blocked

    started = time.time()
    results = [_run(["sdptool", "browse", target], timeout_seconds=25, raw_addresses=raw_addresses)]
    ended = time.time()
    out = output_dir / f"koala_bluez_services_{int(started)}.json"
    payload = BluezRunResult(
        "services",
        _module_title("services"),
        started,
        ended,
        str(output_dir),
        results,
        {"services": str(out)},
        _base_safety(raw_addresses=raw_addresses, owned_device=owned_device),
    )
    _write_json(out, asdict(payload))
    return payload


def gatt_readiness(target: str, owned_device: bool, output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    output_dir = _ensure_output_dir(output_dir)
    blocked = _require_owned_target("gatt-readiness", target, owned_device, output_dir)
    if blocked:
        return blocked

    started = time.time()
    checklist = {
        "theme_title": _module_title("gatt-readiness"),
        "target": redact_addresses(target),
        "owned_device_required": True,
        "operator_checks": [
            "Confirm the device is owned, in written scope, or part of the KoalaByte lab bench.",
            "Record device model, firmware version, and expected GATT service UUIDs before testing.",
            "Use read-only characteristic review first; do not write characteristics without a separate written test plan.",
            "Do not attempt pairing bypass, address spoofing, disruption, or captured-packet replay.",
            "Store screenshots, btmon traces, and notes under the session folder for defensive reporting.",
        ],
        "recommended_safe_commands": [
            "bluetoothctl info <owned-device-address>",
            "bluetoothctl connect <owned-device-address>",
            "bluetoothctl disconnect <owned-device-address>",
        ],
        "blocked_by_default": [
            "unauthorized pairing attempts",
            "unknown-device GATT writes",
            "spoofing",
            "packet replay",
            "disruptive link actions",
        ],
    }
    out = output_dir / f"koala_bluez_gatt_readiness_{int(started)}.json"
    _write_json(out, checklist)
    ended = time.time()
    payload = BluezRunResult(
        "gatt-readiness",
        _module_title("gatt-readiness"),
        started,
        ended,
        str(output_dir),
        [],
        {"gatt_readiness": str(out)},
        _base_safety(raw_addresses=False, owned_device=owned_device),
    )
    summary = output_dir / f"koala_bluez_gatt_readiness_summary_{int(started)}.json"
    _write_json(summary, asdict(payload))
    payload.artifacts["summary"] = str(summary)
    return payload


def all_safe(duration_seconds: int = 15, output_dir: Path = DEFAULT_OUTPUT_DIR, raw_addresses: bool = False) -> List[BluezRunResult]:
    return [
        inventory(output_dir),
        status(output_dir, raw_addresses=raw_addresses),
        scan(duration_seconds, output_dir, raw_addresses=raw_addresses),
    ]


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue Outback BlueZ automation deck")
    parser.add_argument(
        "action",
        choices=[
            "manifest",
            "inventory",
            "status",
            "scan",
            "monitor",
            "info",
            "services",
            "gatt-readiness",
            "all-safe",
        ],
    )
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--target", default=None, help="Owned/scope-approved target address for target-specific diagnostics")
    parser.add_argument("--owned-device", action="store_true", help="Required for target-specific diagnostics")
    parser.add_argument("--raw-addresses", action="store_true", help="Store raw Bluetooth addresses; use only for authorized lab records")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if args.action == "manifest":
        result = module_manifest(output_dir)
    elif args.action == "inventory":
        result = inventory(output_dir)
    elif args.action == "status":
        result = status(output_dir, raw_addresses=args.raw_addresses)
    elif args.action == "scan":
        result = scan(args.duration, output_dir, raw_addresses=args.raw_addresses)
    elif args.action == "monitor":
        result = monitor(args.duration, output_dir)
    elif args.action == "info":
        result = info(args.target or "", args.owned_device, output_dir, raw_addresses=args.raw_addresses)
    elif args.action == "services":
        result = services(args.target or "", args.owned_device, output_dir, raw_addresses=args.raw_addresses)
    elif args.action == "gatt-readiness":
        result = gatt_readiness(args.target or "", args.owned_device, output_dir)
    else:
        results = all_safe(args.duration, output_dir, raw_addresses=args.raw_addresses)
        print(json.dumps([asdict(item) for item in results], indent=2, sort_keys=True))
        return 0

    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
