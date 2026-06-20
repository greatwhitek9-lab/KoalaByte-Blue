from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

DISPLAY_NAME = "didgeridoo"
MODULE_NAME = "KoalaByte Blue Didgeridoo LoRa Setup"
DEFAULT_OUTPUT_DIR = Path("logs/didgeridoo")
DEFAULT_SPI_DEVICE = "/dev/spidev0.0"
DEFAULT_MESHTASTIC_PORT = "/dev/ttyUSB0"

PIN_MAP = {
    "sck": {"gpio": 11, "physical_pin": 23, "signal": "SPI0 SCLK"},
    "miso": {"gpio": 9, "physical_pin": 21, "signal": "SPI0 MISO"},
    "mosi": {"gpio": 10, "physical_pin": 19, "signal": "SPI0 MOSI"},
    "cs": {"gpio": 8, "physical_pin": 24, "signal": "SPI0 CE0"},
    "reset": {"gpio": 22, "physical_pin": 15, "signal": "SX1262 RESET"},
    "busy": {"gpio": 24, "physical_pin": 18, "signal": "SX1262 BUSY"},
    "dio1": {"gpio": 25, "physical_pin": 22, "signal": "SX1262 DIO1 IRQ"},
    "ground": {"physical_pin": 20, "signal": "Ground"},
    "power_3v3": {"physical_pin": 17, "signal": "3.3V power when the board is marked 3V3"},
}

BUTTON_PINS = {
    "button_1_main_menu": {"gpio": 5, "physical_pin": 29},
    "button_2_left_back": {"gpio": 6, "physical_pin": 31},
    "button_3_select": {"gpio": 13, "physical_pin": 33},
    "button_4_right_forward": {"gpio": 19, "physical_pin": 35},
    "button_5_up": {"gpio": 26, "physical_pin": 37},
    "button_6_down": {"gpio": 21, "physical_pin": 40},
    "ground_bus": {"physical_pin": 39},
}


@dataclass(frozen=True)
class DidgeridooStatus:
    display_name: str
    spi_device: str
    spi_device_present: bool
    spidev_python_available: bool
    meshtastic_python_available: bool
    meshtastic_cli_available: bool
    pin_map: Dict[str, Dict[str, object]]
    button_pin_map: Dict[str, Dict[str, object]]
    timestamp: float


def ensure_output_dir(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _spec_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _run_command(args: List[str], timeout: float = 8.0) -> Dict[str, object]:
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


def manifest(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    data = {
        "display_name": DISPLAY_NAME,
        "module_name": MODULE_NAME,
        "revision": "Phase1_Setup_Status_Only",
        "scope": "SX1262 hardware setup, SPI dependency checks, menu integration, and Meshtastic node information only",
        "hardware_target": {
            "module": "DX-LR30 / Semtech SX1262 SPI LoRa board",
            "band_note": "410-475 MHz / 433 MHz module variant",
            "host": "Raspberry Pi 3B+ over 40-pin GPIO breakout",
            "antenna": "433 MHz antenna on the SX1262 SMA connector",
        },
        "safe_boundaries": {
            "raw_radio_sending": False,
            "mesh_text_sending": False,
            "automatic_radio_service": False,
            "status_and_setup_only": True,
        },
        "pin_map": PIN_MAP,
        "button_pin_map": BUTTON_PINS,
        "commands": ["manifest", "status", "meshtastic-info"],
    }
    path = root / "didgeridoo_manifest.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def status(spi_device: str = DEFAULT_SPI_DEVICE, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    status_obj = DidgeridooStatus(
        display_name=DISPLAY_NAME,
        spi_device=spi_device,
        spi_device_present=Path(spi_device).exists(),
        spidev_python_available=_spec_available("spidev"),
        meshtastic_python_available=_spec_available("meshtastic"),
        meshtastic_cli_available=shutil.which("meshtastic") is not None,
        pin_map=PIN_MAP,
        button_pin_map=BUTTON_PINS,
        timestamp=time.time(),
    )
    data = asdict(status_obj)
    data["raspi_config_hint"] = "SPI should be enabled by scripts/setup_system_packages.sh when raspi-config is available. Reboot if /dev/spidev0.0 is missing after first install."
    path = root / "didgeridoo_status.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def meshtastic_info(port: str = DEFAULT_MESHTASTIC_PORT, host: Optional[str] = None, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    if host:
        args = ["meshtastic", "--host", host, "--info"]
    else:
        args = ["meshtastic", "--port", port, "--info"]
    result = _run_command(args, timeout=15.0)
    data = {
        "display_name": DISPLAY_NAME,
        "mode": "meshtastic_node_information_only",
        "port": port if not host else None,
        "host": host,
        "result": result,
        "note": "This command queries a connected Meshtastic node for information only.",
        "timestamp": time.time(),
    }
    path = root / "meshtastic_info.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def print_json(data: Dict[str, object]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KoalaByte Blue didgeridoo LoRa setup/status helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_manifest = sub.add_parser("manifest", help="Write didgeridoo setup manifest")
    p_manifest.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    p_status = sub.add_parser("status", help="Check local SPI and Meshtastic dependency readiness")
    p_status.add_argument("--spi-device", default=DEFAULT_SPI_DEVICE)
    p_status.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    p_info = sub.add_parser("meshtastic-info", help="Read information from a connected Meshtastic node")
    p_info.add_argument("--port", default=DEFAULT_MESHTASTIC_PORT)
    p_info.add_argument("--host", default=None)
    p_info.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def run_cli(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "manifest":
        print_json(manifest(output_dir=args.output_dir))
        return 0
    if args.command == "status":
        print_json(status(spi_device=args.spi_device, output_dir=args.output_dir))
        return 0
    if args.command == "meshtastic-info":
        print_json(meshtastic_info(port=args.port, host=args.host, output_dir=args.output_dir))
        return 0
    raise SystemExit(f"unknown command: {args.command}")
