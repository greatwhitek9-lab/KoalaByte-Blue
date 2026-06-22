from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from .location_password_gate import ensure_unlocked

DISPLAY_NAME = "Meshtastic App"
DEFAULT_LOG_DIR = Path("logs/meshtastic_app")
DEFAULT_PROFILE = Path("logs/meshtastic_app/profile.json")


@dataclass(frozen=True)
class MeshtasticProfile:
    connection: str = "serial"
    port: str = "/dev/ttyUSB0"
    host: str = ""
    ble: str = ""
    label: str = "KoalaByte Heltec Meshtastic Node"


def _log_dir(path: str | Path = DEFAULT_LOG_DIR) -> Path:
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run(args: List[str], timeout: float = 60.0) -> dict[str, object]:
    started = time.time()
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return {"command": args, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "started_at": started, "ended_at": time.time()}
    except FileNotFoundError as exc:
        return {"command": args, "returncode": 127, "stdout": "", "stderr": str(exc), "started_at": started, "ended_at": time.time()}
    except subprocess.TimeoutExpired as exc:
        return {"command": args, "returncode": 124, "stdout": exc.stdout or "", "stderr": "timeout", "started_at": started, "ended_at": time.time()}


def save_profile(profile: MeshtasticProfile, path: str | Path = DEFAULT_PROFILE) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(profile)
    data["created_at"] = time.time()
    data["scope"] = "local Meshtastic node connection profile only; no channel secrets stored"
    target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return {"saved": True, "path": str(target), "profile": data}


def load_profile(path: str | Path = DEFAULT_PROFILE) -> MeshtasticProfile:
    target = Path(path)
    if not target.exists():
        return MeshtasticProfile()
    data = json.loads(target.read_text(encoding="utf-8"))
    return MeshtasticProfile(
        connection=str(data.get("connection", "serial")),
        port=str(data.get("port", "/dev/ttyUSB0")),
        host=str(data.get("host", "")),
        ble=str(data.get("ble", "")),
        label=str(data.get("label", "KoalaByte Heltec Meshtastic Node")),
    )


def connection_args(profile: MeshtasticProfile) -> List[str]:
    if profile.connection == "tcp" and profile.host:
        return ["--host", profile.host]
    if profile.connection == "ble" and profile.ble:
        return ["--ble", profile.ble]
    if profile.connection == "ble":
        return ["--ble"]
    return ["--port", profile.port]


def write_result(name: str, payload: dict[str, object], log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    root = _log_dir(log_dir)
    path = root / f"{name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["artifact_path"] = str(path)
    return payload


def status(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    profile = load_profile()
    result = _run(["meshtastic", *connection_args(profile), "--info"], timeout=25.0)
    payload = {"action": "status", "display_name": DISPLAY_NAME, "profile": asdict(profile), "result": result}
    return write_result("status", payload, log_dir)


def nodes(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    profile = load_profile()
    result = _run(["meshtastic", *connection_args(profile), "--nodes"], timeout=30.0)
    payload = {"action": "nodes", "display_name": DISPLAY_NAME, "profile": asdict(profile), "result": result}
    return write_result("nodes", payload, log_dir)


def listen(seconds: int = 60, password: Optional[str] = None, prompt_password: bool = False, log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    if not ensure_unlocked(password=password, prompt=prompt_password):
        payload = {"action": "listen", "display_name": DISPLAY_NAME, "protected": True, "status": "locked", "note": "protected-actions password required"}
        return write_result("listen_locked", payload, log_dir)
    profile = load_profile()
    result = _run(["meshtastic", *connection_args(profile), "--listen"], timeout=max(5, seconds))
    payload = {"action": "listen", "display_name": DISPLAY_NAME, "protected": True, "profile": asdict(profile), "result": result}
    return write_result("listen", payload, log_dir)


def send_text(message: str, dest: str = "", channel_index: Optional[int] = None, ack: bool = False, confirm_send: bool = False, password: Optional[str] = None, prompt_password: bool = False, log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    if not confirm_send:
        payload = {"action": "send", "display_name": DISPLAY_NAME, "status": "blocked", "reason": "--confirm-send is required"}
        return write_result("send_blocked", payload, log_dir)
    if not ensure_unlocked(password=password, prompt=prompt_password):
        payload = {"action": "send", "display_name": DISPLAY_NAME, "protected": True, "status": "locked", "note": "protected-actions password required"}
        return write_result("send_locked", payload, log_dir)
    profile = load_profile()
    args = ["meshtastic", *connection_args(profile)]
    if channel_index is not None:
        args.extend(["--ch-index", str(channel_index)])
    if dest:
        args.extend(["--dest", dest])
    args.extend(["--sendtext", message])
    if ack:
        args.append("--ack")
    result = _run(args, timeout=45.0)
    payload = {"action": "send", "display_name": DISPLAY_NAME, "protected": True, "profile": asdict(profile), "dest": dest, "channel_index": channel_index, "ack": ack, "result": result}
    return write_result("send", payload, log_dir)


def gps_info(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    profile = load_profile()
    result = _run(["meshtastic", *connection_args(profile), "--info"], timeout=25.0)
    payload = {"action": "gps_info", "display_name": DISPLAY_NAME, "profile": asdict(profile), "result": result, "note": "Use the connected Heltec node's Meshtastic firmware/GNSS status output."}
    return write_result("gps_info", payload, log_dir)


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Password-protected KoalaByte Meshtastic app")
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="Save local Meshtastic connection profile")
    setup.add_argument("--connection", choices=["serial", "tcp", "ble"], default="serial")
    setup.add_argument("--port", default="/dev/ttyUSB0")
    setup.add_argument("--host", default="")
    setup.add_argument("--ble", default="")
    setup.add_argument("--label", default="KoalaByte Heltec Meshtastic Node")
    sub.add_parser("status", help="Show node info")
    sub.add_parser("nodes", help="Show node table")
    sub.add_parser("gps", help="Show GNSS/status information from the node")
    rx = sub.add_parser("listen", help="Password-protected message receive/listen mode")
    rx.add_argument("--seconds", type=int, default=60)
    rx.add_argument("--password", default=None)
    rx.add_argument("--prompt-password", action="store_true")
    tx = sub.add_parser("send", help="Password-protected text send")
    tx.add_argument("--message", required=True)
    tx.add_argument("--dest", default="")
    tx.add_argument("--ch-index", type=int, default=None)
    tx.add_argument("--ack", action="store_true")
    tx.add_argument("--confirm-send", action="store_true")
    tx.add_argument("--password", default=None)
    tx.add_argument("--prompt-password", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "setup":
        print(json.dumps(save_profile(MeshtasticProfile(args.connection, args.port, args.host, args.ble, args.label)), indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        print(json.dumps(status(), indent=2, sort_keys=True))
        return 0
    if args.command == "nodes":
        print(json.dumps(nodes(), indent=2, sort_keys=True))
        return 0
    if args.command == "gps":
        print(json.dumps(gps_info(), indent=2, sort_keys=True))
        return 0
    if args.command == "listen":
        print(json.dumps(listen(args.seconds, password=args.password, prompt_password=args.prompt_password), indent=2, sort_keys=True))
        return 0
    if args.command == "send":
        print(json.dumps(send_text(args.message, dest=args.dest, channel_index=args.ch_index, ack=args.ack, confirm_send=args.confirm_send, password=args.password, prompt_password=args.prompt_password), indent=2, sort_keys=True))
        return 0
    return 1
