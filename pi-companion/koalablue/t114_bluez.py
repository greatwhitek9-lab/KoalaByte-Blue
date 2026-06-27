from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ble_node_manager import BleNodeManager

DEFAULT_OUTPUT_DIR = Path("logs/t114_bluez")
DEFAULT_VALIDATION_PATH = Path("logs/hardware_validation/t114_bluez_validation.json")
DEFAULT_BAUD = 115200


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
    selected_port: str = ""
    controller_mode: str = "combined-safe-serial"
    checks: List[T114ControllerCheck] = field(default_factory=list)
    wrapped_bluez_result: object = None
    t114_serial_events: List[dict[str, Any]] = field(default_factory=list)
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


def _candidate_ports() -> list[str]:
    explicit = [
        os.getenv("KOALABYTE_PRIMARY_BLE_PORT", ""),
        os.getenv("KOALABYTE_HELTEC_USB_PORT", ""),
        os.getenv("HELTEC_PORT", ""),
    ]
    ports: list[str] = [p for p in explicit if p]
    for pattern in ("/dev/koalabyte-heltec", "/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
        ports.extend(sorted(glob.glob(pattern)))
    seen: set[str] = set()
    unique: list[str] = []
    for port in ports:
        if port and port not in seen:
            seen.add(port)
            unique.append(port)
    return unique


def _json_line_exchange(port: str, payloads: list[dict[str, Any]], *, baud: int = DEFAULT_BAUD, seconds: float = 2.5) -> list[dict[str, Any]]:
    import serial  # type: ignore

    events: list[dict[str, Any]] = []
    deadline = time.time() + seconds
    with serial.Serial(port, baudrate=baud, timeout=0.12, write_timeout=0.35) as ser:
        for payload in payloads:
            ser.write((json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"))
        while time.time() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            try:
                event = json.loads(raw.decode("utf-8", errors="replace").strip())
            except Exception:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def _find_combined_serial_port(preferred: str = "", baud: int = DEFAULT_BAUD) -> tuple[str, list[dict[str, Any]]]:
    ports = [preferred] if preferred else []
    ports.extend([p for p in _candidate_ports() if p and p != preferred])
    for port in ports:
        try:
            events = _json_line_exchange(
                port,
                [
                    {"type": "node_roles"},
                    {"type": "ble_status"},
                    {"type": "ble_tx_status"},
                    {"type": "status"},
                ],
                baud=baud,
                seconds=2.0,
            )
        except Exception:
            continue
        if any(evt.get("type") in {"node_roles", "ble_status", "heltec_mouth_status", "ble_tx_status"} for evt in events):
            return port, events
    return "", []


def _detect_adapter_from_bluetoothctl_list(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Controller "):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    return ""


def _dependency_checks() -> list[T114ControllerCheck]:
    checks = [
        _run(["bluetoothctl", "list"]),
        _run(["bluetoothctl", "show"]),
        _run(["btmgmt", "info"]),
        _run(["rfkill", "list", "bluetooth"]),
    ]
    py_check = subprocess.run(
        ["python3", "-c", "import serial, bleak; print('python modules OK: serial, bleak')"],
        capture_output=True,
        text=True,
        check=False,
    ) if shutil.which("python3") else None
    if py_check is None:
        checks.append(T114ControllerCheck(["python3", "-c", "import serial, bleak"], 127, "", "python3 not installed", True, "python3 missing"))
    else:
        checks.append(T114ControllerCheck(["python3", "-c", "import serial, bleak"], py_check.returncode, py_check.stdout, py_check.stderr))
    return checks


def check_controller(adapter: str = "", port: str = "", output_dir: Path = DEFAULT_OUTPUT_DIR, validation_path: Path = DEFAULT_VALIDATION_PATH, baud: int = DEFAULT_BAUD) -> T114BluezResult:
    started = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    checks = _dependency_checks()
    selected_adapter = adapter or _detect_adapter_from_bluetoothctl_list(checks[0].stdout if checks else "")
    selected_port, events = _find_combined_serial_port(port, baud=baud)
    present = bool(selected_port)
    ended = time.time()
    summary = output_dir / f"t114_combined_controller_{int(started)}.json"
    result = T114BluezResult(
        action="controller-check",
        status="ready" if present else "missing_t114_combined_serial",
        started_at=started,
        ended_at=ended,
        output_dir=str(output_dir),
        hci_controller_expected=False,
        hci_controller_present=False,
        selected_adapter=selected_adapter,
        selected_port=selected_port,
        controller_mode="combined-safe-serial",
        checks=checks,
        t114_serial_events=events,
        artifacts={"summary": str(summary), "validation": str(validation_path)},
        safety={
            "authorized_lab_use_only": True,
            "pi_controls_actions": True,
            "t114_nrf52840_primary_ble_radio": True,
            "esp32_s3_secondary_ble_node": True,
            "raspberry_pi_bluez_secondary_node": True,
            "pairing_bypass": False,
            "gatt_writes": False,
            "spoofing": False,
            "packet_replay": False,
            "disruptive_actions": False,
        },
        next_steps=[] if present else [
            "Run the one-shot installer so the T114 combined-safe firmware is flashed.",
            "Confirm /dev/koalabyte-heltec exists or set KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0.",
            "Run: bash scripts/setup_heltec_t114_tools.sh",
        ],
    )
    _write_json(summary, asdict(result))
    _write_json(validation_path, asdict(result))
    return result


def _manifest(output_dir: Path) -> dict[str, Any]:
    payload = {
        "module": "t114_combined_primary_ble",
        "display_name": "Heltec T114 primary BLE radio actions",
        "control_plane": "Raspberry Pi companion",
        "radio_endpoint": "Heltec T114 onboard nRF52840 over USB CDC JSON",
        "secondary_nodes": ["ESP32-S3 DualEye BLE", "Raspberry Pi BlueZ"],
        "dependencies": {
            "apt": ["bluetooth", "bluez", "bluez-tools", "rfkill", "usbutils", "udev"],
            "python": ["pyserial", "bleak"],
            "firmware": "firmware/t114-combined-safe",
            "build_tools": ["west", "nrfutil", "nRF Connect SDK / Zephyr"],
        },
        "actions": ["controller-check", "manifest", "inventory", "status", "scan", "monitor", "all-safe", "tx-status", "lab-advertise-start", "lab-advertise-stop"],
        "safety": "Passive BLE RX by default; TX is bounded non-connectable owned-lab beacon only and requires --confirm-send.",
    }
    path = output_dir / f"t114_combined_manifest_{int(time.time())}.json"
    _write_json(path, payload)
    payload["artifact_path"] = str(path)
    return payload


def _run_node_manager(duration_seconds: int, *, port: str, output_dir: Path, raw_addresses: bool = False) -> list[dict[str, Any]]:
    manager = BleNodeManager(primary_port=port, log_dir=output_dir / "ble_nodes", pi_bluez=True)
    events: list[dict[str, Any]] = []
    duration = None if duration_seconds == 0 else float(duration_seconds)
    for event in manager.run(duration_seconds=duration):
        if not raw_addresses and "addr" in event:
            event = dict(event)
            event["addr_redacted"] = True
            event["addr"] = "redacted"
        events.append(event)
    return events


def _command_tx(action: str, *, port: str, baud: int, name: str, duration_seconds: int, confirm_send: bool) -> list[dict[str, Any]]:
    if action == "tx-status":
        return _json_line_exchange(port, [{"type": "ble_tx_status"}], baud=baud, seconds=2.0)
    if action == "lab-advertise-stop":
        return _json_line_exchange(port, [{"type": "ble_lab_advertise_stop"}], baud=baud, seconds=2.0)
    return _json_line_exchange(
        port,
        [{"type": "ble_lab_advertise_start", "name": name, "duration_ms": max(1, duration_seconds) * 1000, "confirm": bool(confirm_send)}],
        baud=baud,
        seconds=2.0,
    )


def run_wrapped_bluez(action: str, *, adapter: str = "", port: str = "", duration_seconds: int = 15, output_dir: Path = DEFAULT_OUTPUT_DIR, raw_addresses: bool = False, baud: int = DEFAULT_BAUD, tx_name: str = "KoalaByte Lab", confirm_send: bool = False) -> T114BluezResult:
    started = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    validation_path = Path("logs/hardware_validation") / f"t114_combined_{action}_{int(started)}.json"
    controller = check_controller(adapter=adapter, port=port, output_dir=output_dir, validation_path=validation_path, baud=baud)
    if action == "manifest":
        wrapped = _manifest(output_dir)
        controller.action = action
        controller.status = "success"
        controller.wrapped_bluez_result = wrapped
        _write_json(validation_path, asdict(controller))
        return controller
    if action == "inventory":
        controller.action = action
        controller.status = "success" if controller.selected_port else "missing_t114_combined_serial"
        controller.wrapped_bluez_result = {"checks": [asdict(check) for check in controller.checks], "ports": _candidate_ports()}
        _write_json(validation_path, asdict(controller))
        return controller
    if not controller.selected_port:
        controller.action = action
        controller.status = "blocked_missing_t114_combined_serial"
        _write_json(validation_path, asdict(controller))
        return controller

    if action in {"status", "controller-check"}:
        events = _json_line_exchange(controller.selected_port, [{"type": "node_roles"}, {"type": "ble_status"}, {"type": "ble_tx_status"}, {"type": "status"}], baud=baud, seconds=2.0)
        status = "success"
    elif action in {"scan", "monitor", "all-safe"}:
        events = _run_node_manager(duration_seconds, port=controller.selected_port, output_dir=output_dir, raw_addresses=raw_addresses)
        status = "success"
    elif action in {"tx-status", "lab-advertise-start", "lab-advertise-stop"}:
        events = _command_tx(action, port=controller.selected_port, baud=baud, name=tx_name, duration_seconds=duration_seconds, confirm_send=confirm_send)
        status = "success" if events and not any(evt.get("status") == "blocked" for evt in events) else "blocked_or_no_response"
    else:
        raise ValueError(f"Unsupported T114 combined BLE action: {action}")

    ended = time.time()
    summary = output_dir / f"t114_combined_{action}_{int(started)}.json"
    result = T114BluezResult(
        action=action,
        status=status,
        started_at=started,
        ended_at=ended,
        output_dir=str(output_dir),
        hci_controller_expected=False,
        hci_controller_present=False,
        selected_adapter=controller.selected_adapter,
        selected_port=controller.selected_port,
        controller_mode="combined-safe-serial",
        checks=controller.checks,
        wrapped_bluez_result={
            "pi_processed_action": action,
            "duration_seconds": duration_seconds,
            "raw_addresses_requested": raw_addresses,
            "tx_name": tx_name if action.startswith("lab-advertise") else "",
        },
        t114_serial_events=events,
        artifacts={"summary": str(summary), "validation": str(validation_path)},
        safety={
            "authorized_lab_use_only": True,
            "pi_controls_actions": True,
            "t114_nrf52840_primary_ble_transceiver": True,
            "esp32_s3_secondary_ble_node": True,
            "raspberry_pi_bluez_secondary_node": True,
            "bounded_duration_seconds": duration_seconds,
            "tx_requires_confirm_send": action == "lab-advertise-start",
            "tx_non_connectable_owned_lab_beacon_only": action == "lab-advertise-start",
            "raw_addresses_requested": raw_addresses,
            "pairing_bypass": False,
            "gatt_writes": False,
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
    parser = argparse.ArgumentParser(description="KoalaByte Blue Heltec T114 nRF52840 combined BLE action wrapper")
    parser.add_argument("action", nargs="?", default="status", choices=["controller-check", "manifest", "inventory", "status", "scan", "monitor", "all-safe", "tx-status", "lab-advertise-start", "lab-advertise-stop"])
    parser.add_argument("--adapter", default="", help="Optional Linux adapter MAC for secondary BlueZ context only")
    parser.add_argument("--port", default=os.getenv("KOALABYTE_PRIMARY_BLE_PORT", os.getenv("KOALABYTE_HELTEC_USB_PORT", os.getenv("HELTEC_PORT", ""))))
    parser.add_argument("--baud", type=int, default=int(os.getenv("KOALABYTE_BLE_NODE_BAUD", str(DEFAULT_BAUD))))
    parser.add_argument("--duration-seconds", type=int, default=15)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--raw-addresses", action="store_true", help="Keep raw device addresses in local lab artifacts instead of redacting/hashing when supported")
    parser.add_argument("--tx-name", default="KoalaByte Lab", help="Non-connectable lab beacon name for lab-advertise-start")
    parser.add_argument("--confirm-send", action="store_true", help="Required for lab-advertise-start")
    args = parser.parse_args()

    result = run_wrapped_bluez(
        args.action,
        adapter=args.adapter,
        port=args.port,
        duration_seconds=args.duration_seconds,
        output_dir=Path(args.output_dir),
        raw_addresses=args.raw_addresses,
        baud=args.baud,
        tx_name=args.tx_name,
        confirm_send=args.confirm_send,
    )
    _print_json(asdict(result))
    return 0 if result.status in {"ready", "success"} else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
