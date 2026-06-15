from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


DISPLAY_NAME = "Koala Kan Kommander"
ADAPTER_NAME = "InnoMaker USB to CAN Converter kit"
DEFAULT_OUTPUT_DIR = Path("logs/koala_kan_kommander")
CAN_ARPHRD_TYPE = "280"
CAN_FRAME_FMT = "=IB3x8s"
CAN_FRAME_SIZE = struct.calcsize(CAN_FRAME_FMT)


@dataclass(frozen=True)
class CanInterface:
    name: str
    state: str
    mtu: Optional[int]
    qdisc: Optional[str]
    driver_hint: Optional[str]


@dataclass(frozen=True)
class CanFrameRecord:
    timestamp: float
    interface: str
    can_id_hex: str
    dlc: int
    data_hex: str
    is_extended: bool
    is_remote_request: bool
    is_error_frame: bool


def ensure_output_dir(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_command(args: List[str], timeout: float = 5.0) -> Dict[str, object]:
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


def is_can_interface(path: Path) -> bool:
    type_path = path / "type"
    try:
        return type_path.read_text(encoding="utf-8").strip() == CAN_ARPHRD_TYPE
    except OSError:
        return False


def detect_can_interfaces() -> List[CanInterface]:
    interfaces: List[CanInterface] = []
    for iface_path in sorted(Path("/sys/class/net").glob("*")):
        if not is_can_interface(iface_path):
            continue
        name = iface_path.name
        state = "unknown"
        mtu: Optional[int] = None
        try:
            state = (iface_path / "operstate").read_text(encoding="utf-8").strip()
        except OSError:
            pass
        try:
            mtu = int((iface_path / "mtu").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass
        ip_details = run_command(["ip", "-details", "link", "show", name], timeout=3.0)
        stdout = str(ip_details.get("stdout", ""))
        qdisc = None
        if "qdisc" in stdout:
            parts = stdout.split()
            if "qdisc" in parts:
                idx = parts.index("qdisc")
                if idx + 1 < len(parts):
                    qdisc = parts[idx + 1]
        driver_hint = None
        device_link = iface_path / "device" / "driver"
        try:
            driver_hint = os.path.basename(os.readlink(device_link))
        except OSError:
            pass
        interfaces.append(CanInterface(name=name, state=state, mtu=mtu, qdisc=qdisc, driver_hint=driver_hint))
    return interfaces


def manifest(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    data = {
        "display_name": DISPLAY_NAME,
        "revision": "RevA23_InnoMaker_CAN_Update",
        "mode": "innomaker_socketcan_usb_can_commander_plugin",
        "default_interface": "can0",
        "output_dir": str(root),
        "safe_defaults": {
            "passive_listen_only": True,
            "bounded_capture_required": True,
            "raw_can_frame_transmit": False,
            "vehicle_use_requires_written_authorization": True,
        },
        "physical_connection": {
            "recommended_adapter": ADAPTER_NAME,
            "linux_interface_hint": "SocketCAN interface, typically can0 when configured",
            "host_path": "Raspberry Pi 3B+ USB host -> short internal USB data cable -> InnoMaker USB to CAN Converter kit",
            "connector_lines": ["CAN_H", "CAN_L", "GND", "optional SHIELD"],
            "mounting_note": "Mount InnoMaker internally or in a rectangular side/rear service bay; do not use a circular CAN panel port; do not wire CAN directly to Raspberry Pi GPIO.",
        },
        "commands": ["manifest", "inventory", "status", "listen", "report", "transmit-placeholder"],
    }
    path = root / "koala_kan_kommander_manifest.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["manifest_path"] = str(path)
    return data


def inventory(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    interfaces = detect_can_interfaces()
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_NAME,
        "interfaces": [asdict(iface) for iface in interfaces],
        "count": len(interfaces),
        "socketcan_hint": "Install can-utils on the Pi for candump/cansniffer workflows; this module can passively listen through Python raw CAN sockets.",
        "timestamp": time.time(),
    }
    path = root / "can_inventory.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def status(interface: str = "can0", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_NAME,
        "interface": interface,
        "ip_details": run_command(["ip", "-details", "-statistics", "link", "show", interface], timeout=5.0),
        "inventory": [asdict(iface) for iface in detect_can_interfaces()],
        "timestamp": time.time(),
    }
    path = root / f"{interface}_status.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def parse_can_frame(interface: str, raw_frame: bytes) -> CanFrameRecord:
    can_id, dlc, data = struct.unpack(CAN_FRAME_FMT, raw_frame[:CAN_FRAME_SIZE])
    is_eff = bool(can_id & socket.CAN_EFF_FLAG)
    is_rtr = bool(can_id & socket.CAN_RTR_FLAG)
    is_err = bool(can_id & socket.CAN_ERR_FLAG)
    arb_id = can_id & (socket.CAN_EFF_MASK if is_eff else socket.CAN_SFF_MASK)
    payload = data[: min(dlc, 8)]
    return CanFrameRecord(
        timestamp=time.time(),
        interface=interface,
        can_id_hex=f"0x{arb_id:X}",
        dlc=int(dlc),
        data_hex=payload.hex(" ").upper(),
        is_extended=is_eff,
        is_remote_request=is_rtr,
        is_error_frame=is_err,
    )


def listen(interface: str = "can0", duration_seconds: float = 10.0, output_dir: str | Path = DEFAULT_OUTPUT_DIR, max_frames: int = 500) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    records: List[CanFrameRecord] = []
    started = time.time()
    error: Optional[str] = None
    try:
        sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        sock.bind((interface,))
        sock.settimeout(0.25)
        while time.time() - started < duration_seconds and len(records) < max_frames:
            try:
                frame, _addr = sock.recvfrom(CAN_FRAME_SIZE)
            except socket.timeout:
                continue
            records.append(parse_can_frame(interface, frame))
        sock.close()
    except OSError as exc:
        error = str(exc)
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_NAME,
        "interface": interface,
        "duration_seconds": duration_seconds,
        "frame_count": len(records),
        "frames": [asdict(record) for record in records],
        "error": error,
        "safe_mode": "passive_listen_only_no_transmit",
        "timestamp": time.time(),
    }
    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = root / f"{interface}_listen_{stamp}.json"
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(json_path)
    return data


def report(interface: str = "can0", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    inv = inventory(root)
    stat = status(interface, root)
    lines = [
        "# Koala Kan Kommander Report",
        "",
        f"Adapter target: `{ADAPTER_NAME}`",
        f"Interface: `{interface}`",
        f"Detected CAN interfaces: {inv['count']}",
        "",
        "## Safety scope",
        "",
        "This report is for authorized bench or owned-device CAN observation. Raw CAN frame transmission is intentionally not implemented in this plug-in.",
        "",
        "## Mechanical scope",
        "",
        "RevA23 uses the InnoMaker USB-to-CAN adapter mounted internally or in a rectangular service bay. The older circular CAN panel port is not part of this build.",
        "",
        "## Artifacts",
        "",
        f"- Inventory: `{inv.get('artifact_path')}`",
        f"- Status: `{stat.get('artifact_path')}`",
    ]
    path = root / f"{interface}_koala_kan_kommander_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"display_name": DISPLAY_NAME, "report_path": str(path), "inventory": inv, "status": stat}


def blocked_transmit_placeholder(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_NAME,
        "action": "transmit-placeholder",
        "status": "blocked",
        "reason": "Raw CAN frame transmission is intentionally not implemented. Use passive listen/status/report for the production plug-in.",
        "safe_next_step": "Use a bench CAN simulator or owned test harness and document scope before adding any future transmit workflow.",
        "timestamp": time.time(),
    }
    path = root / "transmit_placeholder_blocked.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def run_cli(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Koala Kan Kommander safe InnoMaker SocketCAN plug-in")
    parser.add_argument("action", choices=["manifest", "inventory", "status", "listen", "report", "transmit-placeholder"], nargs="?", default="manifest")
    parser.add_argument("--interface", default="can0", help="SocketCAN interface, for example can0")
    parser.add_argument("--duration", type=float, default=10.0, help="Passive listen duration in seconds")
    parser.add_argument("--max-frames", type=int, default=500, help="Maximum passive frames to record")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.action == "manifest":
        result = manifest(args.output_dir)
    elif args.action == "inventory":
        result = inventory(args.output_dir)
    elif args.action == "status":
        result = status(args.interface, args.output_dir)
    elif args.action == "listen":
        result = listen(args.interface, args.duration, args.output_dir, args.max_frames)
    elif args.action == "report":
        result = report(args.interface, args.output_dir)
    else:
        result = blocked_transmit_placeholder(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())