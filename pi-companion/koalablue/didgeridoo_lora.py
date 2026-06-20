from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

DISPLAY_NAME = "didgeridoo"
MODULE_NAME = "KoalaByte Blue Didgeridoo Meshtastic Node Setup"
DEFAULT_OUTPUT_DIR = Path("logs/didgeridoo")
DEFAULT_SPI_DEVICE = "/dev/spidev0.0"
DEFAULT_MESHTASTIC_PORT = "/dev/ttyUSB0"
DEFAULT_PROFILE_PATH = Path("logs/didgeridoo/meshtastic_login.json")

# The preferred KoalaByte Blue Phase 1 layout is a full USB-C Meshtastic node.
# The SPI pin map remains documented for optional future bare-SX1262 lab work only.
OPTIONAL_SPI_PIN_MAP = {
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
    preferred_connection: str
    detected_serial_ports: List[str]
    meshtastic_python_available: bool
    meshtastic_cli_available: bool
    meshtastic_profile_present: bool
    optional_spi_device: str
    optional_spi_device_present: bool
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


def _profile_path(profile_path: str | Path = DEFAULT_PROFILE_PATH) -> Path:
    return Path(profile_path)


def detect_serial_ports() -> List[str]:
    ports = sorted(set(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")))
    return ports


def load_meshtastic_profile(profile_path: str | Path = DEFAULT_PROFILE_PATH) -> Dict[str, object]:
    path = _profile_path(profile_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_meshtastic_profile(profile: Dict[str, object], profile_path: str | Path = DEFAULT_PROFILE_PATH) -> Dict[str, object]:
    path = _profile_path(profile_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    return {**profile, "profile_path": str(path)}


def build_meshtastic_connection_args(
    port: Optional[str] = None,
    host: Optional[str] = None,
    ble: Optional[str] = None,
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
) -> List[str]:
    if host:
        return ["--host", host]
    if ble:
        return ["--ble", ble]
    if port:
        return ["--port", port]

    profile = load_meshtastic_profile(profile_path)
    connection_type = str(profile.get("connection_type", "serial"))
    if connection_type == "tcp" and profile.get("host"):
        return ["--host", str(profile["host"])]
    if connection_type == "ble" and profile.get("ble"):
        return ["--ble", str(profile["ble"])]
    if profile.get("port"):
        return ["--port", str(profile["port"])]
    return ["--port", DEFAULT_MESHTASTIC_PORT]


def manifest(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    data = {
        "display_name": DISPLAY_NAME,
        "module_name": MODULE_NAME,
        "revision": "Phase1_USB_Meshtastic_Node_First",
        "scope": "USB-C Meshtastic node setup, serial/BLE/TCP login profile, node information, and antenna-routing guidance only",
        "hardware_target": {
            "primary_module": "USB-C Meshtastic LoRa node board",
            "host": "Raspberry Pi 3B+ USB-A port",
            "connection": "short USB-A to USB-C data cable",
            "pi_gpio_required_for_lora": False,
            "legacy_optional_module": "Bare SPI SX1262 module for future lab use only",
        },
        "antenna_plan": {
            "meshtastic_lora_node": "Use one case antenna position for the node's frequency-matched LoRa antenna: 433/868/915 MHz depending on the board and region.",
            "esp32_s3_dualeye": "Keep the second case antenna as a 2.4 GHz Wi-Fi/BLE antenna connected to the ESP32-S3 DualEye IPEX1/U.FL antenna path.",
            "warning": "Do not swap the 2.4 GHz ESP32 antenna and the LoRa antenna; they are different RF systems.",
        },
        "meshtastic_compatibility": {
            "compatible_path": "connect KoalaByte Blue to a Meshtastic firmware node by USB serial, TCP, or BLE and query it with the official meshtastic CLI",
            "phone_app_path": "use the Meshtastic phone app to pair/configure the node, then KoalaByte Blue can connect to the same node by USB serial, TCP, or BLE",
            "login_model": "local connection profile; Meshtastic does not use a KoalaByte username/password login",
        },
        "safe_boundaries": {
            "raw_radio_sending": False,
            "mesh_text_sending": False,
            "automatic_radio_service": False,
            "status_and_setup_only": True,
        },
        "button_pin_map": BUTTON_PINS,
        "optional_spi_pin_map_for_legacy_bare_sx1262": OPTIONAL_SPI_PIN_MAP,
        "commands": ["manifest", "status", "meshtastic-login", "meshtastic-profile", "meshtastic-logout", "meshtastic-info"],
    }
    path = root / "didgeridoo_manifest.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def status(spi_device: str = DEFAULT_SPI_DEVICE, output_dir: str | Path = DEFAULT_OUTPUT_DIR, profile_path: str | Path = DEFAULT_PROFILE_PATH) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    status_obj = DidgeridooStatus(
        display_name=DISPLAY_NAME,
        preferred_connection="USB-C Meshtastic node over /dev/ttyUSB* or /dev/ttyACM*",
        detected_serial_ports=detect_serial_ports(),
        meshtastic_python_available=_spec_available("meshtastic"),
        meshtastic_cli_available=shutil.which("meshtastic") is not None,
        meshtastic_profile_present=_profile_path(profile_path).exists(),
        optional_spi_device=spi_device,
        optional_spi_device_present=Path(spi_device).exists(),
        button_pin_map=BUTTON_PINS,
        timestamp=time.time(),
    )
    data = asdict(status_obj)
    data["usb_hint"] = "Plug the Meshtastic node into the Pi with a USB-A to USB-C data cable, then use /dev/ttyUSB0 or /dev/ttyACM0 in meshtastic-login."
    data["ble_hint"] = "Pair/configure from the phone app first. If the phone app holds the only BLE session, disconnect it before KoalaByte Blue connects."
    data["antenna_hint"] = "One case antenna should be the LoRa node's frequency-matched antenna; the other remains the ESP32-S3 2.4 GHz antenna."
    data["legacy_spi_hint"] = "SPI is optional and only for future direct bare-SX1262 lab work. It is not required for the USB-C Meshtastic node board."
    data["meshtastic_login_hint"] = "Run scripts/run_didgeridoo.py meshtastic-login to save a local serial/TCP/BLE connection profile."
    path = root / "didgeridoo_status.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def meshtastic_login(
    connection_type: str = "serial",
    port: str = DEFAULT_MESHTASTIC_PORT,
    host: Optional[str] = None,
    ble: Optional[str] = None,
    label: str = "KoalaByte Blue Mesh Node",
    verify: bool = False,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    if connection_type not in {"serial", "tcp", "ble"}:
        raise ValueError("connection_type must be serial, tcp, or ble")
    profile = {
        "display_name": DISPLAY_NAME,
        "label": label,
        "connection_type": connection_type,
        "port": port if connection_type == "serial" else None,
        "host": host if connection_type == "tcp" else None,
        "ble": ble if connection_type == "ble" else None,
        "created_at": time.time(),
        "note": "Local Meshtastic connection profile only. No username/password, channel URL, PSK, private key, QR-code secret, or phone-app credential is stored here.",
    }
    saved = save_meshtastic_profile(profile, profile_path=profile_path)
    data: Dict[str, object] = {"profile": saved, "verified": False}
    if verify:
        data["verification"] = meshtastic_info(output_dir=root, profile_path=profile_path)
        result = data["verification"].get("result", {}) if isinstance(data["verification"], dict) else {}
        data["verified"] = isinstance(result, dict) and result.get("returncode") == 0
    path = root / "meshtastic_login_result.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def meshtastic_profile(profile_path: str | Path = DEFAULT_PROFILE_PATH, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    profile = load_meshtastic_profile(profile_path=profile_path)
    data = {
        "display_name": DISPLAY_NAME,
        "profile_present": bool(profile),
        "profile": profile,
        "profile_path": str(_profile_path(profile_path)),
        "timestamp": time.time(),
    }
    path = root / "meshtastic_profile_status.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def meshtastic_logout(profile_path: str | Path = DEFAULT_PROFILE_PATH, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    path = _profile_path(profile_path)
    existed = path.exists()
    if existed:
        path.unlink()
    data = {
        "display_name": DISPLAY_NAME,
        "profile_removed": existed,
        "profile_path": str(path),
        "timestamp": time.time(),
    }
    artifact = root / "meshtastic_logout_result.json"
    artifact.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(artifact)
    return data


def meshtastic_info(
    port: Optional[str] = None,
    host: Optional[str] = None,
    ble: Optional[str] = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    connection_args = build_meshtastic_connection_args(port=port, host=host, ble=ble, profile_path=profile_path)
    result = _run_command(["meshtastic", *connection_args, "--info"], timeout=15.0)
    data = {
        "display_name": DISPLAY_NAME,
        "mode": "meshtastic_node_information_only",
        "connection_args": connection_args,
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
    parser = argparse.ArgumentParser(description="KoalaByte Blue didgeridoo Meshtastic node setup/status helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_manifest = sub.add_parser("manifest", help="Write didgeridoo setup manifest")
    p_manifest.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    p_status = sub.add_parser("status", help="Check local USB serial, optional SPI, and Meshtastic dependency readiness")
    p_status.add_argument("--spi-device", default=DEFAULT_SPI_DEVICE)
    p_status.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p_status.add_argument("--profile-path", default=str(DEFAULT_PROFILE_PATH))

    p_login = sub.add_parser("meshtastic-login", help="Save a local Meshtastic serial/TCP/BLE connection profile")
    p_login.add_argument("--connection", choices=["serial", "tcp", "ble"], default="serial")
    p_login.add_argument("--port", default=DEFAULT_MESHTASTIC_PORT)
    p_login.add_argument("--host", default=None)
    p_login.add_argument("--ble", default=None)
    p_login.add_argument("--label", default="KoalaByte Blue Mesh Node")
    p_login.add_argument("--verify", action="store_true", help="Run meshtastic --info after saving the profile")
    p_login.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p_login.add_argument("--profile-path", default=str(DEFAULT_PROFILE_PATH))

    p_profile = sub.add_parser("meshtastic-profile", help="Show the saved local Meshtastic connection profile")
    p_profile.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p_profile.add_argument("--profile-path", default=str(DEFAULT_PROFILE_PATH))

    p_logout = sub.add_parser("meshtastic-logout", help="Remove the saved local Meshtastic connection profile")
    p_logout.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p_logout.add_argument("--profile-path", default=str(DEFAULT_PROFILE_PATH))

    p_info = sub.add_parser("meshtastic-info", help="Read information from a connected Meshtastic node")
    p_info.add_argument("--port", default=None)
    p_info.add_argument("--host", default=None)
    p_info.add_argument("--ble", default=None)
    p_info.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p_info.add_argument("--profile-path", default=str(DEFAULT_PROFILE_PATH))
    return parser


def run_cli(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "manifest":
        print_json(manifest(output_dir=args.output_dir))
        return 0
    if args.command == "status":
        print_json(status(spi_device=args.spi_device, output_dir=args.output_dir, profile_path=args.profile_path))
        return 0
    if args.command == "meshtastic-login":
        print_json(
            meshtastic_login(
                connection_type=args.connection,
                port=args.port,
                host=args.host,
                ble=args.ble,
                label=args.label,
                verify=args.verify,
                output_dir=args.output_dir,
                profile_path=args.profile_path,
            )
        )
        return 0
    if args.command == "meshtastic-profile":
        print_json(meshtastic_profile(output_dir=args.output_dir, profile_path=args.profile_path))
        return 0
    if args.command == "meshtastic-logout":
        print_json(meshtastic_logout(output_dir=args.output_dir, profile_path=args.profile_path))
        return 0
    if args.command == "meshtastic-info":
        print_json(meshtastic_info(port=args.port, host=args.host, ble=args.ble, output_dir=args.output_dir, profile_path=args.profile_path))
        return 0
    raise SystemExit(f"unknown command: {args.command}")
