#!/usr/bin/env python3
"""KoalaByte Raspberry Pi hardware and runtime doctor.

Read-only by default. It inventories GPIO readiness, InnoMaker SocketCAN,
audio input/output, USB serial aliases, Python dependencies, and systemd
services, then writes a machine-readable report.
"""

from __future__ import annotations

import argparse
import getpass
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
PI_ROOT = ROOT / "pi-companion"
DEFAULT_REPORT = ROOT / "logs" / "pi_hardware" / "pi_hardware_doctor.json"

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

PYTHON_IMPORTS = [
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
]

COMMANDS = [
    "python3",
    "ip",
    "modprobe",
    "lsusb",
    "udevadm",
    "cansend",
    "candump",
    "aplay",
    "arecord",
    "alsamixer",
    "wpctl",
    "pactl",
    "bluetoothctl",
    "rfkill",
    "ffmpeg",
    "espeak-ng",
    "edge-tts",
]

SERVICES = [
    "koalabyte-can0.service",
    "koalabyte-menu.service",
    "koalabyte-menu-sync.service",
    "koalabyte-doctor.service",
    "koalabyte-esp32-dualeye-voice-bridge.service",
    "koalabyte-ble-node-manager.service",
]

SERIAL_ALIASES = [
    "/dev/koalabyte-heltec",
    "/dev/koalabyte-esp32-dualeye",
    "/dev/koalabyte-esp32-face",
    "/dev/koalabyte-primary-ble",
]


def run(command: list[str], timeout: float = 8.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "available": True,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except FileNotFoundError:
        return {"available": False, "returncode": None, "stdout": "", "stderr": "command not found"}
    except subprocess.TimeoutExpired as exc:
        return {
            "available": True,
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": "timed out",
        }
    except Exception as exc:
        return {"available": True, "returncode": None, "stdout": "", "stderr": str(exc)}


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None


def detect_pi() -> dict[str, Any]:
    model_paths = [Path("/proc/device-tree/model"), Path("/sys/firmware/devicetree/base/model")]
    model = next((read_text(path) for path in model_paths if read_text(path)), None)
    return {
        "is_raspberry_pi": bool(model and "raspberry pi" in model.lower()),
        "model": model,
        "machine": platform.machine(),
        "platform": platform.platform(),
        "kernel": platform.release(),
        "python": sys.version,
        "user": getpass.getuser(),
        "uid": os.getuid() if hasattr(os, "getuid") else None,
        "groups": run(["id", "-nG"]).get("stdout", "").split(),
    }


def check_commands() -> dict[str, bool]:
    return {command: shutil.which(command) is not None for command in COMMANDS}


def check_imports() -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for module in PYTHON_IMPORTS:
        try:
            imported = importlib.import_module(module)
            version = getattr(imported, "__version__", None)
            results[module] = {"available": True, "version": str(version) if version else None}
        except Exception as exc:
            results[module] = {"available": False, "error": str(exc)}
    return results


def check_gpio(live: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "mapping": BUTTONS,
        "electrical": {
            "vcc": "Pi 3.3V only",
            "ground": "Pi GND",
            "pull": "internal pull-up",
            "idle": "HIGH",
            "pressed": "LOW",
        },
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


def check_can(interface: str) -> dict[str, Any]:
    interfaces = sorted(path.name for path in Path("/sys/class/net").glob("can*"))
    selected = interface
    if interface == "auto":
        selected = interfaces[0] if interfaces else ""
    details = run(["ip", "-details", "-statistics", "link", "show", selected]) if selected else {
        "available": shutil.which("ip") is not None,
        "returncode": None,
        "stdout": "",
        "stderr": "no can* interface",
    }
    usb = run(["lsusb"])
    usb_matches = [
        line
        for line in usb.get("stdout", "").splitlines()
        if any(token in line.lower() for token in ("innomaker", "usb can", "usb-can", "canable", "candle"))
    ]
    modules = {
        name: Path(f"/sys/module/{name}").exists()
        for name in ("can", "can_raw", "can_dev", "gs_usb")
    }
    return {
        "requested_interface": interface,
        "interfaces": interfaces,
        "selected_interface": selected or None,
        "link": details,
        "kernel_modules": modules,
        "usb_matches": usb_matches,
        "socketcan_ready": bool(selected and details.get("returncode") == 0),
    }


def check_audio() -> dict[str, Any]:
    return {
        "playback_devices": run(["aplay", "-l"]),
        "capture_devices": run(["arecord", "-l"]),
        "pipewire": run(["wpctl", "status"]),
        "pulseaudio": run(["pactl", "info"]),
        "preferred_pattern": os.environ.get("KOALABYTE_AUDIO_SINK_PATTERN", "JBL|USB|speaker|audio"),
    }


def check_serial() -> dict[str, Any]:
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


def check_services() -> dict[str, Any]:
    if shutil.which("systemctl") is None:
        return {"systemd_available": False, "services": {}}
    results: dict[str, Any] = {}
    for service in SERVICES:
        enabled = run(["systemctl", "is-enabled", service])
        active = run(["systemctl", "is-active", service])
        results[service] = {
            "enabled": enabled.get("stdout") or enabled.get("stderr"),
            "enabled_rc": enabled.get("returncode"),
            "active": active.get("stdout") or active.get("stderr"),
            "active_rc": active.get("returncode"),
        }
    return {"systemd_available": True, "services": results}


def derive_findings(payload: dict[str, Any]) -> tuple[str, list[str]]:
    findings: list[str] = []
    pi = payload["pi"]
    if not pi["is_raspberry_pi"]:
        findings.append("Host does not identify itself as a Raspberry Pi.")
    needed_groups = {"gpio", "dialout", "audio", "video", "render", "plugdev"}
    missing_groups = sorted(needed_groups.difference(pi.get("groups", [])))
    if missing_groups:
        findings.append("Service user is missing optional hardware groups: " + ", ".join(missing_groups))
    missing_commands = sorted(name for name, present in payload["commands"].items() if not present)
    if missing_commands:
        findings.append("Missing host commands: " + ", ".join(missing_commands))
    missing_imports = sorted(
        name for name, result in payload["python_imports"].items() if not result.get("available")
    )
    if missing_imports:
        findings.append("Missing Python imports: " + ", ".join(missing_imports))
    if not payload["can"]["socketcan_ready"]:
        findings.append("No ready SocketCAN interface was detected.")
    playback = payload["audio"]["playback_devices"]
    if playback.get("returncode") != 0:
        findings.append("No ALSA playback inventory was available.")
    capture = payload["audio"]["capture_devices"]
    if capture.get("returncode") != 0:
        findings.append("No ALSA capture inventory was available.")
    if not any(item["exists"] for item in payload["serial"]["aliases"].values()):
        findings.append("KoalaByte stable serial aliases are not present yet.")
    status = "PI_HARDWARE_READY" if not findings else "PI_HARDWARE_NEEDS_ATTENTION"
    return status, findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory KoalaByte Raspberry Pi hardware and runtime readiness")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--can-interface", default=os.environ.get("CAN_INTERFACE", "can0"))
    parser.add_argument("--gpio-live", action="store_true", help="Open K1-K8 inputs and read their current states")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when findings remain")
    args = parser.parse_args()

    if str(PI_ROOT) not in sys.path:
        sys.path.insert(0, str(PI_ROOT))

    payload: dict[str, Any] = {
        "pi": detect_pi(),
        "commands": check_commands(),
        "python_imports": check_imports(),
        "gpio": check_gpio(args.gpio_live),
        "can": check_can(args.can_interface),
        "audio": check_audio(),
        "serial": check_serial(),
        "services": check_services(),
        "repo_root": str(ROOT),
        "updated_at": time.time(),
    }
    status, findings = derive_findings(payload)
    payload["status"] = status
    payload["findings"] = findings

    report = Path(args.report)
    if not report.is_absolute():
        report = ROOT / report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(status)
    print(f"Pi: {payload['pi'].get('model') or payload['pi']['platform']}")
    print(f"GPIO live read: {payload['gpio']['live_read']}")
    print(f"CAN interfaces: {', '.join(payload['can']['interfaces']) or 'none'}")
    print(f"Serial aliases: {sum(1 for item in payload['serial']['aliases'].values() if item['exists'])}")
    if findings:
        for finding in findings:
            print(f"- {finding}")
    else:
        print("- No readiness findings.")
    print(f"Report: {report}")

    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
