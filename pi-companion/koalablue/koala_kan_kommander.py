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
LAB_SAFE_ID_MIN = 0x600
LAB_SAFE_ID_MAX = 0x67F
MAX_GENERATED_FRAMES = 64
PAYLOAD_SCHEMA_VERSION = "koala-kan-payload-batch-v1"


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


@dataclass(frozen=True)
class CanPayloadSpec:
    label: str
    can_id_hex: str
    dlc: int
    data_hex: str
    is_extended: bool
    is_remote_request: bool
    repeat_ms: int
    note: str


PAYLOAD_PROFILE_CHOICES = ["heartbeat", "counter", "walking-bit", "ascii-tag", "all"]


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
        "revision": "RevA24_Kan_Payload_Generator",
        "mode": "innomaker_socketcan_usb_can_commander_plugin",
        "default_interface": "can0",
        "output_dir": str(root),
        "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
        "safe_defaults": {
            "passive_listen_only": True,
            "bounded_capture_required": True,
            "raw_can_frame_transmit": False,
            "synthetic_payload_generation": True,
            "payload_transmit_contract_only": True,
            "vehicle_use_requires_written_authorization": True,
        },
        "payload_generator": {
            "profiles": PAYLOAD_PROFILE_CHOICES,
            "default_lab_id_range": f"0x{LAB_SAFE_ID_MIN:X}-0x{LAB_SAFE_ID_MAX:X}",
            "max_generated_frames": MAX_GENERATED_FRAMES,
            "excludes": [
                "UDS diagnostic services",
                "OBD requests",
                "OEM or vehicle-specific arbitration IDs",
                "actuator, immobilizer, steering, braking, lighting, lock, or powertrain commands",
            ],
        },
        "physical_connection": {
            "recommended_adapter": ADAPTER_NAME,
            "linux_interface_hint": "SocketCAN interface, typically can0 when configured",
            "host_path": "Raspberry Pi 3B+ USB host -> short internal USB data cable -> InnoMaker USB to CAN Converter kit",
            "connector_lines": ["CAN_H", "CAN_L", "GND", "optional SHIELD"],
            "mounting_note": "Mount InnoMaker internally or in a rectangular side/rear service bay; do not use a circular CAN panel port; do not wire CAN directly to Raspberry Pi GPIO.",
        },
        "commands": ["manifest", "inventory", "status", "listen", "report", "generate-payloads", "transmit-placeholder"],
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


def parse_lab_base_id(value: str | int) -> int:
    if isinstance(value, int):
        can_id = value
    else:
        text = str(value).strip().lower()
        try:
            can_id = int(text, 16) if text.startswith("0x") else int(text, 10)
        except ValueError as exc:
            raise ValueError(f"invalid CAN base ID '{value}'") from exc
    if not (LAB_SAFE_ID_MIN <= can_id <= LAB_SAFE_ID_MAX - 3):
        raise ValueError(
            f"base ID must reserve four standard lab IDs in range 0x{LAB_SAFE_ID_MIN:X}-0x{LAB_SAFE_ID_MAX:X}; "
            f"use 0x{LAB_SAFE_ID_MIN:X}-0x{LAB_SAFE_ID_MAX - 3:X}"
        )
    return can_id


def clamp_sequence_count(sequence_count: int) -> int:
    if sequence_count < 1:
        raise ValueError("sequence count must be at least 1")
    return min(sequence_count, MAX_GENERATED_FRAMES)


def normalize_ascii_tag(tag: str) -> bytes:
    cleaned = "".join(ch for ch in str(tag).upper() if 32 <= ord(ch) <= 126)
    if not cleaned:
        cleaned = "KOALAKAN"
    return cleaned.encode("ascii", errors="ignore")[:8].ljust(8, b" ")


def make_payload(label: str, can_id: int, payload: bytes, repeat_ms: int, note: str) -> CanPayloadSpec:
    bounded = payload[:8].ljust(8, b"\x00")
    return CanPayloadSpec(
        label=label,
        can_id_hex=f"0x{can_id:X}",
        dlc=len(bounded),
        data_hex=bounded.hex(" ").upper(),
        is_extended=False,
        is_remote_request=False,
        repeat_ms=max(0, int(repeat_ms)),
        note=note,
    )


def socketcan_preview(interface: str, frame: CanPayloadSpec) -> str:
    arb_id = frame.can_id_hex.removeprefix("0x").removeprefix("0X")
    data = frame.data_hex.replace(" ", "")
    return f"{interface} {arb_id}#{data}"


def build_payload_specs(profile: str, base_id: int, sequence_count: int, tag: str, repeat_ms: int) -> List[CanPayloadSpec]:
    count = clamp_sequence_count(sequence_count)
    frames: List[CanPayloadSpec] = []
    selected_profiles = ["heartbeat", "counter", "walking-bit", "ascii-tag"] if profile == "all" else [profile]
    for selected in selected_profiles:
        if selected == "heartbeat":
            for idx in range(count):
                frames.append(
                    make_payload(
                        label=f"heartbeat-{idx:02d}",
                        can_id=base_id,
                        payload=bytes([0x4B, 0x42, 0x48, idx & 0xFF, 0x00, 0x00, 0x00, 0x00]),
                        repeat_ms=repeat_ms,
                        note="Synthetic KoalaByte heartbeat frame for a bench CAN simulator.",
                    )
                )
        elif selected == "counter":
            for idx in range(count):
                frames.append(
                    make_payload(
                        label=f"counter-{idx:02d}",
                        can_id=base_id + 1,
                        payload=bytes([0x4B, 0x42, idx & 0xFF, (~idx) & 0xFF, (idx * 3) & 0xFF, 0x00, 0x00, 0x00]),
                        repeat_ms=repeat_ms,
                        note="Synthetic monotonic counter pattern for parser/display validation.",
                    )
                )
        elif selected == "walking-bit":
            for idx in range(count):
                bit_index = idx % 64
                payload = bytearray(8)
                payload[bit_index // 8] = 1 << (bit_index % 8)
                frames.append(
                    make_payload(
                        label=f"walking-bit-{idx:02d}",
                        can_id=base_id + 2,
                        payload=bytes(payload),
                        repeat_ms=repeat_ms,
                        note="Synthetic walking-bit pattern for display and bitfield decoder checks.",
                    )
                )
        elif selected == "ascii-tag":
            frames.append(
                make_payload(
                    label="ascii-tag",
                    can_id=base_id + 3,
                    payload=normalize_ascii_tag(tag),
                    repeat_ms=repeat_ms,
                    note="Synthetic ASCII lab tag; padded to one classic CAN data frame.",
                )
            )
        else:
            raise ValueError(f"unsupported payload profile '{profile}'")
    return frames[:MAX_GENERATED_FRAMES]


def generate_payloads(
    interface: str = "can0",
    profile: str = "all",
    base_id: str | int = "0x600",
    sequence_count: int = 8,
    tag: str = "KOALAKAN",
    repeat_ms: int = 1000,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if profile not in PAYLOAD_PROFILE_CHOICES:
        error = f"profile must be one of: {', '.join(PAYLOAD_PROFILE_CHOICES)}"
        frames: List[CanPayloadSpec] = []
        status_value = "blocked"
    else:
        try:
            safe_base_id = parse_lab_base_id(base_id)
            frames = build_payload_specs(profile, safe_base_id, sequence_count, tag, repeat_ms)
            error = None
            status_value = "generated"
        except ValueError as exc:
            frames = []
            error = str(exc)
            status_value = "blocked"
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_NAME,
        "action": "generate-payloads",
        "status": status_value,
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "interface_hint": interface,
        "profile": profile,
        "requested_base_id": str(base_id),
        "allowed_lab_id_range": f"0x{LAB_SAFE_ID_MIN:X}-0x{LAB_SAFE_ID_MAX:X}",
        "frame_count": len(frames),
        "frames": [asdict(frame) for frame in frames],
        "socketcan_preview_lines": [socketcan_preview(interface, frame) for frame in frames],
        "transmit_function_contract": {
            "compatible_fields": ["can_id_hex", "dlc", "data_hex", "is_extended", "is_remote_request", "repeat_ms"],
            "required_gate": "owned bench harness or isolated CAN simulator only",
            "production_transmit_default": "blocked",
        },
        "safety_scope": {
            "allowed": "Synthetic lab payloads for parser, display, logging, and bench-harness validation.",
            "excluded": [
                "No UDS, OBD, DTC, ECU reset, security-access, or diagnostic-session payloads.",
                "No vehicle, battery, industrial controller, actuator, lock, lighting, steering, braking, powertrain, or immobilizer payloads.",
                "No OEM arbitration IDs or captured traffic replay.",
            ],
        },
        "error": error,
        "timestamp": time.time(),
    }
    path = root / f"{interface}_payloads_{profile}_{stamp}.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def report(interface: str = "can0", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    inv = inventory(root)
    stat = status(interface, root)
    payload_batch = generate_payloads(interface=interface, profile="all", output_dir=root)
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
        "The payload generator creates synthetic lab frames for parser, display, logging, and simulator validation only.",
        "",
        "## Mechanical scope",
        "",
        "RevA23 uses the InnoMaker USB-to-CAN adapter mounted internally or in a rectangular service bay. The older circular CAN panel port is not part of this build.",
        "",
        "## Artifacts",
        "",
        f"- Inventory: `{inv.get('artifact_path')}`",
        f"- Status: `{stat.get('artifact_path')}`",
        f"- Synthetic payload batch: `{payload_batch.get('artifact_path')}`",
    ]
    path = root / f"{interface}_koala_kan_kommander_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"display_name": DISPLAY_NAME, "report_path": str(path), "inventory": inv, "status": stat, "payload_batch": payload_batch}


def blocked_transmit_placeholder(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Dict[str, object]:
    root = ensure_output_dir(output_dir)
    data = {
        "display_name": DISPLAY_NAME,
        "adapter_target": ADAPTER_NAME,
        "action": "transmit-placeholder",
        "status": "blocked",
        "reason": "Raw CAN frame transmission is intentionally not implemented. Use passive listen/status/report and generate-payloads for bench-only transmit-compatible payload artifacts.",
        "safe_next_step": "Use a bench CAN simulator or owned isolated test harness and document scope before adding any future transmit workflow.",
        "timestamp": time.time(),
    }
    path = root / "transmit_placeholder_blocked.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def run_cli(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Koala Kan Kommander safe InnoMaker SocketCAN plug-in")
    parser.add_argument(
        "action",
        choices=["manifest", "inventory", "status", "listen", "report", "generate-payloads", "transmit-placeholder"],
        nargs="?",
        default="manifest",
    )
    parser.add_argument("--interface", default="can0", help="SocketCAN interface, for example can0")
    parser.add_argument("--duration", type=float, default=10.0, help="Passive listen duration in seconds")
    parser.add_argument("--max-frames", type=int, default=500, help="Maximum passive frames to record")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--payload-profile", choices=PAYLOAD_PROFILE_CHOICES, default="all", help="Synthetic payload generator profile")
    parser.add_argument("--base-id", default="0x600", help="Bench-only standard CAN base ID; reserves base through base+3")
    parser.add_argument("--sequence-count", type=int, default=8, help=f"Generated frames per sequence profile, capped at {MAX_GENERATED_FRAMES}")
    parser.add_argument("--tag", default="KOALAKAN", help="ASCII tag for the ascii-tag payload profile")
    parser.add_argument("--repeat-ms", type=int, default=1000, help="Suggested repeat interval metadata for downstream bench transmit tooling")
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
    elif args.action == "generate-payloads":
        result = generate_payloads(
            interface=args.interface,
            profile=args.payload_profile,
            base_id=args.base_id,
            sequence_count=args.sequence_count,
            tag=args.tag,
            repeat_ms=args.repeat_ms,
            output_dir=args.output_dir,
        )
    else:
        result = blocked_transmit_placeholder(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
