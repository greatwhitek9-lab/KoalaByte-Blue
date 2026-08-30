#!/usr/bin/env python3
"""Read-only KoalaByte Raspberry Pi hardware and runtime inventory."""

from __future__ import annotations

import argparse
import getpass
import grp
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "logs" / "pi_hardware" / "pi_hardware_doctor.json"
VENV_BIN = ROOT / "pi-companion" / ".venv" / "bin"

BUTTONS = {
    "K1": {"bcm": 5, "physical": 29, "label": "Main Menu"},
    "K2": {"bcm": 6, "physical": 31, "label": "Move Left / Back"},
    "K3": {"bcm": 13, "physical": 33, "label": "Enter / Select"},
    "K4": {"bcm": 19, "physical": 35, "label": "Move Right / Forward"},
    "K5": {"bcm": 26, "physical": 37, "label": "Up"},
    "K6": {"bcm": 21, "physical": 40, "label": "Down"},
    "K7": {"bcm": 20, "physical": 38, "label": "Power On/Off", "hold_seconds": 2.5},
    "K8": {"bcm": 16, "physical": 36, "label": "Reset / Reboot", "hold_seconds": 3.0},
}

CORE_COMMANDS = (
    "python3",
    "ip",
    "lsusb",
    "udevadm",
    "aplay",
    "arecord",
    "bluetoothctl",
    "rfkill",
    "ffmpeg",
    "espeak-ng",
)

OPTIONAL_COMMANDS = (
    "candump",
    "cansend",
    "wpctl",
    "pactl",
)

PYTHON_IMPORTS = (
    "serial",
    "bleak",
    "gpiozero",
    "pygame",
    "can",
    "speech_recognition",
    "pyttsx3",
    "fastapi",
    "uvicorn",
    "requests",
    "httpx",
)

SERVICES = (
    "koalabyte-menu.service",
    "koalabyte-hdmi.service",
    "koalabyte-doctor.service",
    "koalabyte-dualeye-voice-bridge.service",
    "koalabyte-ble-node-manager.service",
)

SERIAL_ALIASES = (
    "/dev/koalabyte-heltec",
    "/dev/koalabyte-heltec-t114",
    "/dev/koalabyte-esp32-dualeye",
)


def run(command: list[str], timeout: float = 8.0) -> dict[str, Any]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "available": True,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except FileNotFoundError:
        return {"available": False, "returncode": None, "stdout": "", "stderr": "command not found"}
    except subprocess.TimeoutExpired:
        return {"available": True, "returncode": None, "stdout": "", "stderr": "timed out"}
    except Exception as exc:
        return {"available": True, "returncode": None, "stdout": "", "stderr": str(exc)}


def read_pi_model() -> str | None:
    for path in (Path("/proc/device-tree/model"), Path("/sys/firmware/devicetree/base/model")):
        try:
            value = path.read_text(encoding="utf-8", errors="ignore").strip("\x00\n ")
            if value:
                return value
        except Exception:
            pass
    return None


def detect_pi() -> dict[str, Any]:
    model = read_pi_model()
    groups = run(["id", "-nG"]).get("stdout", "").split()
    throttled = run(["vcgencmd", "get_throttled"]) if shutil.which("vcgencmd") else {
        "available": False,
        "returncode": None,
        "stdout": "",
        "stderr": "vcgencmd unavailable",
    }
    return {
        "is_raspberry_pi": bool(model and "raspberry pi" in model.lower()),
        "model": model,
        "machine": platform.machine(),
        "platform": platform.platform(),
        "kernel": platform.release(),
        "python": sys.version,
        "user": getpass.getuser(),
        "uid": os.getuid() if hasattr(os, "getuid") else None,
        "groups": groups,
        "power_throttle": throttled,
    }


def command_inventory() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for command in CORE_COMMANDS + OPTIONAL_COMMANDS:
        result[command] = {"available": shutil.which(command) is not None, "path": shutil.which(command)}
    edge = shutil.which("edge-tts") or (str(VENV_BIN / "edge-tts") if (VENV_BIN / "edge-tts").exists() else None)
    result["edge-tts"] = {"available": edge is not None, "path": edge}
    return result


def import_inventory() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for module in PYTHON_IMPORTS:
        try:
            imported = importlib.import_module(module)
            version = getattr(imported, "__version__", None)
            result[module] = {"available": True, "version": str(version) if version else None}
        except Exception as exc:
            result[module] = {"available": False, "error": str(exc)}
    return result


def gpio_inventory(live: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "mapping": BUTTONS,
        "electrical": {"vcc": "Pi 3.3V only", "ground": "Pi GND", "pull": "internal pull-up", "idle": "HIGH", "pressed": "LOW"},
        "live_requested": live,
        "live_read": False,
        "pin_states": {},
    }
    if not live:
        return result
    try:
        from gpiozero import Button  # type: ignore

        devices = []
        try:
            for key, cfg in BUTTONS.items():
                button = Button(int(cfg["bcm"]), pull_up=True, bounce_time=0.05)
                devices.append(button)
                result["pin_states"][key] = {
                    "pressed": bool(button.is_pressed),
                    "electrical": "LOW" if button.is_pressed else "HIGH",
                }
            result["live_read"] = True
        finally:
            for device in devices:
                device.close()
    except Exception as exc:
        result["error"] = str(exc)
    return result


def can_inventory(interface: str) -> dict[str, Any]:
    interfaces = sorted(path.name for path in Path("/sys/class/net").glob("can*"))
    selected = interfaces[0] if interface == "auto" and interfaces else interface
    present = bool(selected and Path(f"/sys/class/net/{selected}").exists())
    policy = os.getenv("INSTALL_INNOMAKER_CAN", "auto").strip().lower()
    required = policy in {"1", "true", "yes", "on", "required"}
    return {
        "policy": policy,
        "required": required,
        "interfaces": interfaces,
        "selected_interface": selected or None,
        "socketcan_ready": present,
        "link": run(["ip", "-details", "-statistics", "link", "show", selected]) if present else None,
        "kernel_modules": {name: Path(f"/sys/module/{name}").exists() for name in ("can", "can_raw", "can_dev", "gs_usb")},
    }


def audio_inventory() -> dict[str, Any]:
    return {
        "playback_devices": run(["aplay", "-l"]),
        "capture_devices": run(["arecord", "-l"]),
        "pipewire": run(["wpctl", "status"]),
        "pulseaudio": run(["pactl", "info"]),
        "preferred_pattern": os.getenv("KOALABYTE_AUDIO_SINK_PATTERN", "JBL|USB|speaker|audio"),
    }


def serial_inventory() -> dict[str, Any]:
    aliases: dict[str, Any] = {}
    for raw in SERIAL_ALIASES:
        path = Path(raw)
        aliases[raw] = {
            "exists": path.exists(),
            "is_symlink": path.is_symlink(),
            "target": str(path.resolve()) if path.exists() else None,
        }
    by_id = Path("/dev/serial/by-id")
    return {
        "aliases": aliases,
        "by_id": sorted(str(path) for path in by_id.glob("*")) if by_id.exists() else [],
        "tty_acm": sorted(str(path) for path in Path("/dev").glob("ttyACM*")),
        "tty_usb": sorted(str(path) for path in Path("/dev").glob("ttyUSB*")),
    }


def hdmi_inventory() -> dict[str, Any]:
    connectors: dict[str, str] = {}
    for path in sorted(Path("/sys/class/drm").glob("card*-HDMI-*/status")):
        try:
            connectors[str(path)] = path.read_text(encoding="utf-8").strip().lower()
        except OSError as exc:
            connectors[str(path)] = f"unreadable: {exc}"

    state_root = Path(
        os.getenv("KOALABYTE_HDMI_STATE_DIR", str(ROOT / "logs" / "hdmi"))
    )
    mode = "koalabyte"
    mode_payload: dict[str, Any] = {}
    mode_path = state_root / "display_mode.json"
    try:
        raw = json.loads(mode_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            mode_payload = raw
            candidate = str(raw.get("mode") or "").strip().lower()
            if candidate in {"koalabyte", "desktop"}:
                mode = candidate
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    service_status: dict[str, Any] = {}
    status_path = state_root / "hdmi_display_status.json"
    try:
        raw = json.loads(status_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            service_status = raw
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    return {
        "policy": os.getenv("KOALABYTE_HDMI", "auto"),
        "connected": any(value == "connected" for value in connectors.values()),
        "connectors": connectors,
        "mode": mode,
        "mode_state": mode_payload,
        "service_status": service_status,
        "state_root": str(state_root),
        "read_only_renderer": True,
        "serial_ports_opened": False,
    }


def service_inventory(include_can: bool) -> dict[str, Any]:
    names = list(SERVICES)
    if include_can:
        names.append("koalabyte-can0.service")
    if shutil.which("systemctl") is None:
        return {"systemd_available": False, "services": {}}
    result: dict[str, Any] = {}
    for service in names:
        enabled = run(["systemctl", "is-enabled", service])
        active = run(["systemctl", "is-active", service])
        result[service] = {
            "enabled": enabled.get("stdout") or enabled.get("stderr"),
            "enabled_rc": enabled.get("returncode"),
            "active": active.get("stdout") or active.get("stderr"),
            "active_rc": active.get("returncode"),
        }
    return {"systemd_available": True, "services": result}


def power_control_inventory() -> dict[str, Any]:
    path = Path("/etc/sudoers.d/90-koalabyte-power-controls")
    result: dict[str, Any] = {
        "path": str(path),
        "exists": None,
        "accessible": True,
        "valid": None,
    }
    try:
        result["exists"] = path.exists()
    except PermissionError as exc:
        result["accessible"] = False
        result["error"] = str(exc)
        return result
    except OSError as exc:
        result["accessible"] = False
        result["error"] = str(exc)
        return result

    if result["exists"] and shutil.which("visudo"):
        if os.geteuid() == 0:
            check = run(["visudo", "-cf", str(path)])
            result["valid"] = check.get("returncode") == 0
            result["validation"] = check
        else:
            # The service account intentionally cannot read /etc/sudoers.d on a
            # hardened install. Do not request extra privilege from a read-only
            # doctor; the installer validates this rule when it is installed.
            result["validation_skipped"] = "unprivileged doctor; installer owns sudoers validation"
    return result


def derive_findings(payload: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    findings: list[str] = []
    notes: list[str] = []
    pi = payload["pi"]
    if not pi["is_raspberry_pi"]:
        findings.append("Host does not identify itself as a Raspberry Pi.")
    else:
        needed_groups = {"gpio", "dialout", "audio", "video", "render", "plugdev"}
        try:
            grp.getgrnam("input")
            needed_groups.add("input")
        except KeyError:
            pass
        missing_groups = sorted(needed_groups.difference(pi.get("groups", [])))
        if missing_groups:
            findings.append("Service user is missing hardware groups: " + ", ".join(missing_groups))
        throttle_text = str(pi.get("power_throttle", {}).get("stdout", ""))
        if throttle_text and throttle_text != "throttled=0x0":
            findings.append("Raspberry Pi reports current or historical undervoltage/throttling: " + throttle_text)

    missing_commands = sorted(name for name in CORE_COMMANDS if not payload["commands"][name]["available"])
    if missing_commands:
        findings.append("Missing core host commands: " + ", ".join(missing_commands))
    if not payload["commands"]["edge-tts"]["available"]:
        findings.append("William TTS command edge-tts is unavailable.")

    missing_imports = sorted(name for name, item in payload["python_imports"].items() if not item.get("available"))
    if missing_imports:
        findings.append("Missing Python imports: " + ", ".join(missing_imports))

    if payload["can"]["required"] and not payload["can"]["socketcan_ready"]:
        findings.append("SocketCAN is required by policy but no ready interface was detected.")
    elif not payload["can"]["socketcan_ready"]:
        notes.append("Optional SocketCAN adapter is not present; CAN setup is skipped.")

    if not payload["hdmi"]["connected"]:
        notes.append("No connected HDMI connector was detected; the optional compositor remains idle.")
    elif payload["hdmi"]["mode"] == "desktop":
        notes.append("HDMI is connected and currently released to Raspberry Pi OS/console.")
    else:
        notes.append("HDMI is connected and currently assigned to the KoalaByte display.")

    if not any(item["exists"] for item in payload["serial"]["aliases"].values()):
        findings.append("KoalaByte stable serial aliases are not present.")

    power_controls = payload["power_controls"]
    if power_controls.get("accessible") is False:
        notes.append("Restricted K7/K8 sudoers rule is protected from the unprivileged doctor; installer validation remains authoritative.")
    elif power_controls.get("exists") is False:
        findings.append("Restricted K7/K8 power-control sudoers rule is not installed.")
    elif power_controls.get("valid") is False:
        findings.append("Restricted K7/K8 power-control sudoers rule is invalid.")

    status = "PI_HARDWARE_READY" if not findings else "PI_HARDWARE_NEEDS_ATTENTION"
    return status, findings, notes


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory KoalaByte Raspberry Pi hardware and optional-HDMI runtime readiness")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--can-interface", default=os.getenv("CAN_INTERFACE", "can0"))
    parser.add_argument("--gpio-live", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    can = can_inventory(args.can_interface)
    payload: dict[str, Any] = {
        "pi": detect_pi(),
        "commands": command_inventory(),
        "python_imports": import_inventory(),
        "gpio": gpio_inventory(args.gpio_live),
        "can": can,
        "audio": audio_inventory(),
        "hdmi": hdmi_inventory(),
        "serial": serial_inventory(),
        "power_controls": power_control_inventory(),
        "services": service_inventory(can["required"] or can["socketcan_ready"]),
        "updated_at": time.time(),
    }
    status, findings, notes = derive_findings(payload)
    payload["status"] = status
    payload["findings"] = findings
    payload["notes"] = notes

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(status)
    print(f"Pi: {payload['pi'].get('model') or payload['pi'].get('platform')}")
    print(f"GPIO live read: {payload['gpio'].get('live_read')}")
    print(f"CAN interfaces: {', '.join(can['interfaces']) if can['interfaces'] else 'none (optional)'}")
    print(f"HDMI: {'connected' if payload['hdmi']['connected'] else 'not connected (optional)'} / {payload['hdmi']['mode']}")
    print(f"Serial aliases: {sum(1 for item in payload['serial']['aliases'].values() if item['exists'])}")
    for finding in findings:
        print(f"- {finding}")
    for note in notes:
        print(f"- Note: {note}")
    print(f"Report: {report}")
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
