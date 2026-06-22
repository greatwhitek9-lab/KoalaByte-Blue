from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Iterable, Optional

DISPLAY_NAME = "Koala Kan Commander Firmware Track"
ADAPTER_TARGET = "InnoMaker USB to CAN Converter kit"
DEFAULT_OUTPUT_DIR = Path("logs/koala_kan_kommander")
FIRMWARE_DIR = Path("firmware/innomaker-can-commander")


def ensure_output_dir(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_command(args: list[str], timeout: float = 5.0) -> dict[str, object]:
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "command": args,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {"command": args, "returncode": 127, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {"command": args, "returncode": 124, "stdout": exc.stdout or "", "stderr": "command timed out"}


def safety_scope() -> dict[str, object]:
    return {
        "default_path": "Use the InnoMaker adapter stock firmware through Linux SocketCAN. No firmware flash is required for Koala Kan Kommander.",
        "optional_track": "A custom CAN Commander-style adapter firmware is possible only after confirming the exact MCU, bootloader access, CAN transceiver pins, clock tree, USB pins, and a way to restore stock firmware.",
        "allowed": [
            "Owned bench simulator or fully isolated owned harness only.",
            "Adapter identification, firmware planning, and non-destructive status checks.",
            "Generic USB CDC or gs_usb-style CAN bridge behavior for lab frames only after hardware confirmation.",
        ],
        "blocked_by_default": [
            "No default reflashing of the InnoMaker kit.",
            "No vehicle-specific payload library.",
            "No diagnostic, security-access, immobilizer, braking, steering, lock, lighting, or powertrain command set.",
            "No captured traffic replay mode.",
        ],
    }


def manifest(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    root = ensure_output_dir(output_dir)
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_TARGET,
        "firmware_dir": str(FIRMWARE_DIR),
        "firmware_flash_required_for_normal_koala_kan": False,
        "recommended_normal_path": "SocketCAN can0 with can-utils and python-can",
        "experimental_custom_firmware_track": True,
        "status": "available_as_planning_and_board-qualification_track",
        "safe_scope": safety_scope(),
        "candidate_firmware_interfaces": [
            "stock SocketCAN-compatible adapter firmware",
            "gs_usb / candleLight-style USB CAN bridge, only if hardware supports it",
            "USB CDC JSON bridge using the Koala Kan Commander protocol, only for a confirmed custom board profile",
        ],
        "required_before_any_flash": [
            "Identify the exact MCU marking and board revision.",
            "Photograph both sides of the adapter PCB clearly.",
            "Confirm bootloader, BOOT/RESET, SWD, or DFU access.",
            "Confirm CAN controller/transceiver wiring and oscillator/clock source.",
            "Back up or source the stock firmware / recovery image.",
            "Use an isolated bench simulator, not a vehicle or production network.",
        ],
        "commands": ["manifest", "status", "plan"],
        "timestamp": time.time(),
    }
    path = root / "koala_kan_commander_firmware_manifest.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def status(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    root = ensure_output_dir(output_dir)
    commands = {
        "lsusb": run_command(["lsusb"], timeout=5.0),
        "ip_link": run_command(["ip", "link"], timeout=5.0),
        "dfu_util_available": bool(shutil.which("dfu-util")),
        "st_flash_available": bool(shutil.which("st-flash")),
        "openocd_available": bool(shutil.which("openocd")),
        "python_can_available": run_command(["python3", "-c", "import can; print(can.__version__)"], timeout=5.0),
    }
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_TARGET,
        "action": "firmware-status",
        "firmware_flash_required_for_normal_koala_kan": False,
        "non_destructive": True,
        "commands": commands,
        "next_step": "Use SocketCAN normally. Only continue to custom firmware after board identification and stock firmware recovery are confirmed.",
        "safe_scope": safety_scope(),
        "timestamp": time.time(),
    }
    path = root / "koala_kan_commander_firmware_status.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def plan(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    root = ensure_output_dir(output_dir)
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_TARGET,
        "action": "firmware-plan",
        "decision": "possible_but_not_default",
        "why_not_default": [
            "The InnoMaker kit already works as a USB CAN adapter through Linux SocketCAN.",
            "Replacing adapter firmware can brick the adapter if the MCU, bootloader, pins, and recovery process are wrong.",
            "Koala Kan Kommander already provides safe host-side command, listen, manifest, report, and gated bench transmit workflows without firmware replacement.",
        ],
        "safe_inclusion_in_suite": [
            "Keep setup_can0.sh and SocketCAN as the production path.",
            "Include firmware/innomaker-can-commander as an experimental board-qualification track.",
            "Require explicit board profile and recovery proof before adding any flash helper.",
            "Keep payload generation synthetic and lab-range only.",
        ],
        "candidate_protocol": {
            "transport": "USB CDC JSON or gs_usb-compatible USB CAN bridge",
            "host_to_adapter": ["hello", "get_status", "set_bitrate", "start_listen", "stop_listen", "tx_frame_lab"],
            "adapter_to_host": ["boot", "status", "rx_frame", "tx_ack", "error"],
            "default_bitrate": 500000,
            "lab_id_range": "0x600-0x67F",
            "captured_replay": False,
        },
        "safe_scope": safety_scope(),
        "timestamp": time.time(),
    }
    path = root / "koala_kan_commander_firmware_plan.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def run_cli(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Koala Kan Commander optional firmware track manager")
    parser.add_argument("action", choices=["manifest", "status", "plan"], nargs="?", default="manifest")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.action == "manifest":
        result = manifest(args.output_dir)
    elif args.action == "status":
        result = status(args.output_dir)
    else:
        result = plan(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
