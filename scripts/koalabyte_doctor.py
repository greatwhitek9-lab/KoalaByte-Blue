#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
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

STATUS_PATH = ROOT / "logs" / "doctor" / "koalabyte_doctor_status.json"

COMMAND_GROUPS = {
    "core": ["python3", "bash", "git"],
    "bluez": ["bluetoothctl", "btmon", "btmgmt", "rfkill"],
    "serial_usb": ["lsusb", "udevadm"],
    "flash_build": ["cmake", "ninja", "west"],
    "optional_legacy_bluez": ["hciconfig", "hcitool", "rfcomm", "l2ping", "gatttool", "btproxy", "sdptool"],
    "optional_can": ["ip", "cansend", "candump"],
    "optional_audio": ["aplay"],
}

IMPORTANT_PATHS = [
    "install.sh",
    "scripts/install_koalabyte_one_shot.sh",
    "scripts/check_repo_readiness.py",
    "scripts/check_menu_actions.py",
    "scripts/check_menu_display_sync.py",
    "scripts/check_one_shot_controls.py",
    "scripts/preflight_all_hardware.py",
    "scripts/koalabyte_safe_mode.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/export_koalabyte_logs.sh",
    "scripts/run_koalabyte_status_server.py",
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/t114-combined-safe/CMakeLists.txt",
    "systemd/koalabyte-menu.service",
    "udev/99-koalabyte-blue.rules",
]

STATUS_FILES = [
    "logs/one_shot_install_status.json",
    "logs/one_shot/menu_display_sync_status.json",
    "logs/one_shot/control_surface_status.json",
    "logs/killerkoala/ollama_setup_status.json",
    "logs/koala_bluez/gatttool_setup_status.json",
    "logs/koalabyte_external_antenna_status.json",
    "logs/can/innomaker_optional_status.json",
    "logs/anteater/status.json",
]

CHECKS = [
    [sys.executable, "scripts/check_repo_readiness.py"],
    [sys.executable, "scripts/check_menu_actions.py"],
    [sys.executable, "scripts/check_menu_display_sync.py"],
    [sys.executable, "scripts/check_one_shot_controls.py"],
    [sys.executable, "scripts/preflight_all_hardware.py", "--profile", "heltec"],
    ["bash", "scripts/setup_bluez_gatttool.sh", "--check-only"],
    ["bash", "scripts/setup_killerkoala_ollama.sh", "--check-only"],
    ["bash", "scripts/configure_koalabyte_external_antennas.sh", "--check-only"],
]


def run_cmd(cmd: list[str], *, timeout: int = 45) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "PYTHONPATH": f"{PI_ROOT}{os.pathsep}{ROOT}{os.pathsep}" + os.environ.get("PYTHONPATH", "")},
        )
        return {
            "command": cmd,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout_tail": proc.stdout[-3000:],
            "stderr_tail": proc.stderr[-3000:],
            "duration_seconds": round(time.time() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": cmd,
            "returncode": 124,
            "ok": False,
            "stdout_tail": (exc.stdout or "")[-3000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-3000:] if isinstance(exc.stderr, str) else "timeout",
            "duration_seconds": round(time.time() - started, 3),
        }
    except Exception as exc:
        return {
            "command": cmd,
            "returncode": 1,
            "ok": False,
            "stdout_tail": "",
            "stderr_tail": str(exc),
            "duration_seconds": round(time.time() - started, 3),
        }


def command_inventory() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for group, commands in COMMAND_GROUPS.items():
        out[group] = {}
        for command in commands:
            path = shutil.which(command)
            out[group][command] = {"available": bool(path), "path": path or ""}
    return out


def path_inventory() -> dict[str, bool]:
    return {relative: (ROOT / relative).exists() for relative in IMPORTANT_PATHS}


def status_file_inventory() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for relative in STATUS_FILES:
        path = ROOT / relative
        if not path.exists():
            out[relative] = {"present": False}
            continue
        try:
            out[relative] = {"present": True, "json": json.loads(path.read_text(encoding="utf-8"))}
        except Exception as exc:
            out[relative] = {"present": True, "error": str(exc), "size_bytes": path.stat().st_size}
    return out


def disk_memory_status() -> dict[str, Any]:
    total, used, free = shutil.disk_usage(ROOT)
    meminfo: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", 1)
            meminfo[key] = int(value.strip().split()[0])
    except Exception:
        pass
    return {
        "disk": {"total_mb": total // 1024 // 1024, "used_mb": used // 1024 // 1024, "free_mb": free // 1024 // 1024},
        "memory_kb": {key: meminfo.get(key, 0) for key in ["MemTotal", "MemAvailable", "SwapTotal", "SwapFree"]},
    }


def build_report(*, quick: bool = False, strict: bool = False) -> dict[str, Any]:
    checks = [] if quick else [run_cmd(cmd) for cmd in CHECKS]
    command_status = command_inventory()
    paths = path_inventory()

    failures: list[str] = []
    for relative, present in paths.items():
        if not present:
            failures.append(f"missing path: {relative}")
    for check in checks:
        if not check.get("ok"):
            failures.append("check failed: " + " ".join(check.get("command", [])))
    if strict:
        for group in ["core", "bluez", "serial_usb"]:
            for command, info in command_status[group].items():
                if not info["available"]:
                    failures.append(f"missing required command in strict mode: {command}")

    return {
        "status": "KOALABYTE_DOCTOR_READY" if not failures else "KOALABYTE_DOCTOR_WARNINGS",
        "updated_at": time.time(),
        "strict": strict,
        "quick": quick,
        "repo_root": str(ROOT),
        "commands": command_status,
        "paths": paths,
        "status_files": status_file_inventory(),
        "system": disk_memory_status(),
        "checks": checks,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run KoalaByte Blue post-install diagnostics")
    parser.add_argument("--quick", action="store_true", help="Skip subprocess readiness checks and only inspect local status/files")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on warnings and missing core commands")
    parser.add_argument("--output", default=str(STATUS_PATH), help="Path to write the doctor JSON report")
    args = parser.parse_args()

    report = build_report(quick=args.quick, strict=args.strict)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output), "failures": report["failures"]}, indent=2, sort_keys=True))
    return 1 if args.strict and report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
