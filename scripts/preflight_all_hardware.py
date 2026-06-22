#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "logs" / "preflight"


def run(args: list[str], timeout: float = 5.0) -> dict[str, object]:
    try:
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        return {"command": args, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except FileNotFoundError as exc:
        return {"command": args, "returncode": 127, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired:
        return {"command": args, "returncode": 124, "stdout": "", "stderr": "command timed out"}


def command_ok(name: str) -> bool:
    return shutil.which(name) is not None


def module_ok(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def load_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="KoalaByte full non-flashing hardware/software preflight report")
    parser.add_argument("--profile", choices=["main", "heltec", "auto"], default="auto")
    parser.add_argument("--setup-vcan", action="store_true", help="create vcan0 before running the vcan Koala Kan checks")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when required checks are missing")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    profile = args.profile
    if profile == "auto":
        profile = "heltec" if (ROOT / "firmware" / "heltec-mouth").exists() else "main"

    discovery = run([sys.executable, "scripts/discover_koalabyte_ports.py", "--profile", profile, "--output-dir", str(OUT_DIR)])
    ports = load_json(OUT_DIR / "koalabyte_ports.json")

    if args.setup_vcan:
        vcan_setup = run(["bash", "scripts/setup_vcan0.sh"])
    else:
        vcan_setup = {"skipped": True, "reason": "pass --setup-vcan to create vcan0"}

    checks = {
        "commands": {
            "lsusb": command_ok("lsusb"),
            "ip": command_ok("ip"),
            "modprobe": command_ok("modprobe"),
            "cansend": command_ok("cansend"),
            "candump": command_ok("candump"),
            "python3": command_ok("python3"),
            "systemctl": command_ok("systemctl"),
            "udevadm": command_ok("udevadm"),
        },
        "python_modules": {
            "can": module_ok("can"),
            "serial": module_ok("serial"),
            "bleak": module_ok("bleak"),
        },
        "repo_files": {
            "setup_can0": (ROOT / "scripts" / "setup_can0.sh").exists(),
            "setup_vcan0": (ROOT / "scripts" / "setup_vcan0.sh").exists(),
            "install_can0_service": (ROOT / "scripts" / "install_can0_service.sh").exists(),
            "install_udev_rules": (ROOT / "scripts" / "install_koalabyte_udev_rules.sh").exists(),
            "ble_node_manager": (ROOT / "scripts" / "run_ble_node_manager.py").exists(),
        },
    }

    can_iface = str(ports.get("ports", {}).get("can_interface", "can0") if isinstance(ports.get("ports"), dict) else "can0")
    vcan_iface = str(ports.get("ports", {}).get("vcan_interface", "vcan0") if isinstance(ports.get("ports"), dict) else "vcan0")

    report = {
        "profile": profile,
        "timestamp": time.time(),
        "discovery_command": discovery,
        "ports": ports.get("ports", {}),
        "checks": checks,
        "vcan_setup": vcan_setup,
        "interface_status": {
            "can": run(["ip", "-details", "link", "show", can_iface]),
            "vcan": run(["ip", "-details", "link", "show", vcan_iface]),
        },
        "koala_kan_non_flashing_checks": {
            "manifest_can": run([sys.executable, "scripts/run_koala_kan_kommander.py", "manifest", "--interface", can_iface]),
            "status_can": run([sys.executable, "scripts/run_koala_kan_kommander.py", "status", "--interface", can_iface]),
            "manifest_vcan": run([sys.executable, "scripts/run_koala_kan_kommander.py", "manifest", "--interface", vcan_iface]),
            "status_vcan": run([sys.executable, "scripts/run_koala_kan_kommander.py", "status", "--interface", vcan_iface]),
        },
    }

    required_ok = all(checks["commands"][name] for name in ["ip", "python3"]) and checks["repo_files"]["setup_can0"] and checks["repo_files"]["ble_node_manager"]
    if profile == "heltec":
        primary_found = bool(ports.get("ports", {}).get("heltec") if isinstance(ports.get("ports"), dict) else False)
    else:
        primary_found = bool(ports.get("ports", {}).get("nrf_ble") if isinstance(ports.get("ports"), dict) else False)
    report["summary"] = {
        "required_repo_tools_present": required_ok,
        "profile_primary_port_found": primary_found,
        "can_utils_present": checks["commands"]["cansend"] and checks["commands"]["candump"],
        "python_can_present": checks["python_modules"]["can"],
        "safe_to_attempt_flash_after_review": required_ok and primary_found,
    }

    out_path = OUT_DIR / "hardware_report.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"report": str(out_path), "summary": report["summary"]}, indent=2, sort_keys=True))

    if args.strict and not (required_ok and primary_found and checks["python_modules"]["can"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
