from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from .location_password_gate import ensure_unlocked

DISPLAY_NAME = "Meshtastic App"
DEFAULT_LOG_DIR = Path("logs/meshtastic_app")
DEFAULT_PROFILE = Path("logs/meshtastic_app/profile.json")
DEFAULT_SEND_PROMPT = Path("logs/meshtastic_app/send_prompt.json")
DEFAULT_SERIAL_PORT = os.getenv("KOALABYTE_MESHTASTIC_PORT") or os.getenv("KOALABYTE_HELTEC_USB_PORT") or os.getenv("KOALABYTE_PRIMARY_BLE_PORT") or "/dev/koalabyte-heltec"
DEFAULT_TCP_HOST = os.getenv("KOALABYTE_MESHTASTIC_HOST") or os.getenv("MESHTASTIC_HOST") or ""
DEFAULT_BLE_TARGET = os.getenv("KOALABYTE_MESHTASTIC_BLE") or os.getenv("MESHTASTIC_BLE") or ""
DEFAULT_ESP32_PORT = os.getenv("KOALABYTE_MESHTASTIC_ESP32_PORT") or os.getenv("MESHTASTIC_ESP32_PORT") or "/dev/ttyUSB0"

PRESET_SEND_MESSAGES = {
    "test": "Test from KoalaByte Blue",
    "checkin": "KoalaByte Blue check-in",
    "online": "KoalaByte Blue is online",
}


@dataclass(frozen=True)
class MeshtasticProfile:
    connection: str = "serial"
    port: str = DEFAULT_SERIAL_PORT
    host: str = DEFAULT_TCP_HOST
    ble: str = DEFAULT_BLE_TARGET
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


def meshtastic_cli_available() -> bool:
    return shutil.which("meshtastic") is not None


def save_profile(profile: MeshtasticProfile, path: str | Path = DEFAULT_PROFILE) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(profile)
    data["created_at"] = time.time()
    data["scope"] = "local Meshtastic node connection profile only; no channel secrets stored"
    target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return {"saved": True, "path": str(target), "profile": data}


def env_profile() -> MeshtasticProfile:
    connection = (os.getenv("KOALABYTE_MESHTASTIC_CONNECTION") or os.getenv("MESHTASTIC_CONNECTION") or "serial").lower()
    if connection not in {"serial", "tcp", "ble"}:
        connection = "serial"
    return MeshtasticProfile(
        connection=connection,
        port=os.getenv("KOALABYTE_MESHTASTIC_PORT") or os.getenv("KOALABYTE_HELTEC_USB_PORT") or os.getenv("KOALABYTE_PRIMARY_BLE_PORT") or DEFAULT_SERIAL_PORT,
        host=os.getenv("KOALABYTE_MESHTASTIC_HOST") or os.getenv("MESHTASTIC_HOST") or DEFAULT_TCP_HOST,
        ble=os.getenv("KOALABYTE_MESHTASTIC_BLE") or os.getenv("MESHTASTIC_BLE") or DEFAULT_BLE_TARGET,
        label=os.getenv("KOALABYTE_MESHTASTIC_LABEL") or "KoalaByte Heltec Meshtastic Node",
    )


def load_profile(path: str | Path = DEFAULT_PROFILE) -> MeshtasticProfile:
    target = Path(path)
    if not target.exists():
        return env_profile()
    data = json.loads(target.read_text(encoding="utf-8"))
    return MeshtasticProfile(
        connection=str(data.get("connection", "serial")),
        port=str(data.get("port", DEFAULT_SERIAL_PORT)),
        host=str(data.get("host", DEFAULT_TCP_HOST)),
        ble=str(data.get("ble", DEFAULT_BLE_TARGET)),
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


def _env_confirm_send() -> Optional[bool]:
    value = os.getenv("KOALABYTE_MESHTASTIC_CONFIRM_SEND")
    if value is None:
        return None
    return value in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}


def default_send_prompt_state() -> dict[str, object]:
    confirm_env = _env_confirm_send()
    channel_env = os.getenv("KOALABYTE_MESHTASTIC_CHANNEL_INDEX", "")
    return {
        "message": os.getenv("KOALABYTE_MESHTASTIC_SEND_MESSAGE", ""),
        "dest": os.getenv("KOALABYTE_MESHTASTIC_SEND_DEST", ""),
        "channel_index": int(channel_env) if channel_env.isdigit() else None,
        "confirm_send": bool(confirm_env) if confirm_env is not None else False,
        "source": "environment" if os.getenv("KOALABYTE_MESHTASTIC_SEND_MESSAGE") else "default",
    }


def load_send_prompt_state(path: str | Path = DEFAULT_SEND_PROMPT) -> dict[str, object]:
    state = default_send_prompt_state()
    target = Path(path)
    if target.exists():
        try:
            saved = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                state.update(saved)
                state["source"] = "menu_saved"
        except Exception as exc:
            state["load_error"] = str(exc)
    if os.getenv("KOALABYTE_MESHTASTIC_SEND_MESSAGE"):
        state["message"] = os.getenv("KOALABYTE_MESHTASTIC_SEND_MESSAGE", "")
        state["source"] = "environment"
    confirm_env = _env_confirm_send()
    if confirm_env is not None:
        state["confirm_send"] = confirm_env
    if os.getenv("KOALABYTE_MESHTASTIC_SEND_DEST"):
        state["dest"] = os.getenv("KOALABYTE_MESHTASTIC_SEND_DEST", "")
    channel_env = os.getenv("KOALABYTE_MESHTASTIC_CHANNEL_INDEX", "")
    if channel_env.isdigit():
        state["channel_index"] = int(channel_env)
    return state


def save_send_prompt_state(state: dict[str, object], path: str | Path = DEFAULT_SEND_PROMPT) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    clean = {
        "message": str(state.get("message", "")),
        "dest": str(state.get("dest", "")),
        "channel_index": state.get("channel_index") if isinstance(state.get("channel_index"), int) else None,
        "confirm_send": bool(state.get("confirm_send", False)),
        "updated_at": time.time(),
        "scope": "menu-managed Meshtastic send prompt; no channel secrets stored",
    }
    target.write_text(json.dumps(clean, indent=2, sort_keys=True), encoding="utf-8")
    return {"saved": True, "path": str(target), "send_prompt": clean}


def send_prompt_status(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    state = load_send_prompt_state()
    payload = {"action": "send_prompt_status", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_SEND_PROMPT_READY", "send_prompt": state, "path": str(DEFAULT_SEND_PROMPT)}
    return write_result("send_prompt_status", payload, log_dir)


def set_send_message_preset(preset: str = "test", log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    message = PRESET_SEND_MESSAGES.get(preset, PRESET_SEND_MESSAGES["test"])
    state = load_send_prompt_state()
    state["message"] = message
    state["confirm_send"] = False
    saved = save_send_prompt_state(state)
    payload = {"action": "set_send_message_preset", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_SEND_MESSAGE_SET", "preset": preset, **saved}
    return write_result("set_send_message_preset", payload, log_dir)


def set_send_confirm(enabled: bool, log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    state = load_send_prompt_state()
    state["confirm_send"] = bool(enabled)
    saved = save_send_prompt_state(state)
    payload = {"action": "set_send_confirm", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_SEND_CONFIRM_ON" if enabled else "MESHTASTIC_SEND_CONFIRM_OFF", **saved}
    return write_result("set_send_confirm", payload, log_dir)


def clear_send_prompt(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    saved = save_send_prompt_state({"message": "", "dest": "", "channel_index": None, "confirm_send": False})
    payload = {"action": "clear_send_prompt", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_SEND_PROMPT_CLEARED", **saved}
    return write_result("clear_send_prompt", payload, log_dir)


def profile_status(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    profile = load_profile()
    payload = {
        "action": "profile",
        "display_name": DISPLAY_NAME,
        "status": "MESHTASTIC_PROFILE_READY",
        "profile": asdict(profile),
        "profile_path": str(DEFAULT_PROFILE),
        "send_prompt": load_send_prompt_state(),
        "meshtastic_cli_available": meshtastic_cli_available(),
        "connection_args": connection_args(profile),
        "compatibility": compatibility_matrix(include_profile=False),
    }
    return write_result("profile", payload, log_dir)


def compatibility_matrix(include_profile: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "iphone_android_app": {"supported": True, "mode": "Pair the official Meshtastic phone app directly to the Heltec/ESP32 Meshtastic node over BLE, or use the app's network/TCP option when the node is reachable on the same LAN.", "koalabyte_role": "KoalaByte can use the same node through serial, TCP, or BLE for status, nodes, GPS, and protected listen/send helpers."},
        "heltec_t114": {"supported": True, "recommended_pi_connection": "serial", "default_port": DEFAULT_SERIAL_PORT, "radio_role": "primary BLE/GNSS/LoRa board for KoalaByte; Meshtastic app node when flashed/configured for Meshtastic use."},
        "esp32_meshtastic_device": {"supported": True, "recommended_pi_connections": ["serial", "tcp", "ble"], "default_serial_port": DEFAULT_ESP32_PORT, "notes": "ESP32 Meshtastic boards can be used as an external Meshtastic node when they expose USB serial, BLE, or TCP/network access."},
        "safety": {"channel_secrets_stored": False, "send_requires_confirm_send": True, "listen_and_send_require_protected_gate": True},
        "meshtastic_cli_available": meshtastic_cli_available(),
    }
    if include_profile:
        payload["profile"] = asdict(load_profile())
        payload["send_prompt"] = load_send_prompt_state()
    return payload


def compatibility_status(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    payload = {"action": "compatibility", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_COMPATIBILITY_READY", **compatibility_matrix()}
    return write_result("compatibility", payload, log_dir)


def phone_pairing_guide(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    payload = {"action": "phone_pairing", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_PHONE_APP_READY", "iphone_android": {"pairing_mode": "Use the Meshtastic iPhone/Android app to pair directly to the Heltec or ESP32 Meshtastic node over BLE.", "koalabyte_parallel_access": "KoalaByte can keep a local CLI profile for serial, BLE, or TCP status checks. Do not store channel secrets in KoalaByte logs.", "recommended_flow": ["Flash/configure the Heltec or ESP32 device with Meshtastic firmware using the normal Meshtastic app/tooling.", "Pair the phone app to that node and set region/channel settings in the phone app.", "Use KoalaByte's Meshtastic Status, Nodes, and GPS Info actions to read local node state from the same node when connected."]}, "profile": asdict(load_profile()), "send_prompt": load_send_prompt_state(), "meshtastic_cli_available": meshtastic_cli_available()}
    return write_result("phone_pairing", payload, log_dir)


def esp32_device_guide(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    payload = {"action": "esp32_device", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_ESP32_DEVICE_READY", "esp32_meshtastic_device": {"supported": True, "serial_setup_env": "KOALABYTE_MESHTASTIC_ESP32_PORT=/dev/ttyUSB0", "tcp_setup_env": "KOALABYTE_MESHTASTIC_HOST=<node-ip>", "ble_setup_env": "KOALABYTE_MESHTASTIC_BLE=<ble-name-or-address>", "note": "This is for a separate ESP32 device running Meshtastic firmware. It is separate from the ESP32-S3 DualEye face board unless that board is intentionally flashed as a Meshtastic node."}, "profile": asdict(load_profile()), "send_prompt": load_send_prompt_state(), "meshtastic_cli_available": meshtastic_cli_available()}
    return write_result("esp32_device", payload, log_dir)


def setup_serial(port: str = "", label: str = "KoalaByte Heltec Meshtastic Node", log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    selected_port = port or os.getenv("KOALABYTE_MESHTASTIC_PORT") or os.getenv("KOALABYTE_HELTEC_USB_PORT") or os.getenv("KOALABYTE_PRIMARY_BLE_PORT") or DEFAULT_SERIAL_PORT
    payload = save_profile(MeshtasticProfile(connection="serial", port=selected_port, label=label))
    payload.update({"action": "setup_serial", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_SERIAL_PROFILE_SAVED", "meshtastic_cli_available": meshtastic_cli_available()})
    return write_result("setup_serial", payload, log_dir)


def setup_tcp(host: str = "", label: str = "KoalaByte Network Meshtastic Node", log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    selected_host = host or os.getenv("KOALABYTE_MESHTASTIC_HOST") or os.getenv("MESHTASTIC_HOST") or ""
    if not selected_host:
        payload = {"action": "setup_tcp", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_TCP_HOST_REQUIRED", "required_env": "KOALABYTE_MESHTASTIC_HOST=<node-ip>", "profile": asdict(load_profile())}
        return write_result("setup_tcp_required", payload, log_dir)
    payload = save_profile(MeshtasticProfile(connection="tcp", host=selected_host, label=label))
    payload.update({"action": "setup_tcp", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_TCP_PROFILE_SAVED", "meshtastic_cli_available": meshtastic_cli_available()})
    return write_result("setup_tcp", payload, log_dir)


def setup_ble(ble: str = "", label: str = "KoalaByte BLE Meshtastic Node", log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    selected_ble = ble or os.getenv("KOALABYTE_MESHTASTIC_BLE") or os.getenv("MESHTASTIC_BLE") or ""
    payload = save_profile(MeshtasticProfile(connection="ble", ble=selected_ble, label=label))
    payload.update({"action": "setup_ble", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_BLE_PROFILE_SAVED", "note": "Blank BLE target lets the meshtastic CLI scan/select when supported.", "meshtastic_cli_available": meshtastic_cli_available()})
    return write_result("setup_ble", payload, log_dir)


def status(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    profile = load_profile()
    result = _run(["meshtastic", *connection_args(profile), "--info"], timeout=25.0)
    payload = {"action": "status", "display_name": DISPLAY_NAME, "profile": asdict(profile), "result": result, "meshtastic_cli_available": meshtastic_cli_available()}
    return write_result("status", payload, log_dir)


def nodes(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    profile = load_profile()
    result = _run(["meshtastic", *connection_args(profile), "--nodes"], timeout=30.0)
    payload = {"action": "nodes", "display_name": DISPLAY_NAME, "profile": asdict(profile), "result": result, "meshtastic_cli_available": meshtastic_cli_available()}
    return write_result("nodes", payload, log_dir)


def listen(seconds: int = 60, password: Optional[str] = None, prompt_password: bool = False, log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    if not ensure_unlocked(password=password, prompt=prompt_password):
        payload = {"action": "listen", "display_name": DISPLAY_NAME, "protected": True, "status": "locked", "note": "protected-actions password required"}
        return write_result("listen_locked", payload, log_dir)
    profile = load_profile()
    result = _run(["meshtastic", *connection_args(profile), "--listen"], timeout=max(5, seconds))
    payload = {"action": "listen", "display_name": DISPLAY_NAME, "protected": True, "profile": asdict(profile), "result": result, "meshtastic_cli_available": meshtastic_cli_available()}
    return write_result("listen", payload, log_dir)


def send_text(message: str, dest: str = "", channel_index: Optional[int] = None, ack: bool = False, confirm_send: bool = False, password: Optional[str] = None, prompt_password: bool = False, log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    if not confirm_send:
        payload = {"action": "send", "display_name": DISPLAY_NAME, "status": "blocked", "reason": "confirmation is required"}
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
    payload = {"action": "send", "display_name": DISPLAY_NAME, "protected": True, "profile": asdict(profile), "dest": dest, "channel_index": channel_index, "ack": ack, "result": result, "meshtastic_cli_available": meshtastic_cli_available()}
    return write_result("send", payload, log_dir)


def send_from_prompt(password: Optional[str] = None, prompt_password: bool = False, log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    state = load_send_prompt_state()
    message = str(state.get("message", ""))
    dest = str(state.get("dest", ""))
    channel_index = state.get("channel_index") if isinstance(state.get("channel_index"), int) else None
    confirm_send = bool(state.get("confirm_send", False))
    if not message:
        payload = {"action": "send_from_prompt", "display_name": DISPLAY_NAME, "status": "MESHTASTIC_SEND_PROMPT_EMPTY", "send_prompt": state, "next_menu_step": "Choose Set Test Message or Set Check-In Message, then Confirm Send ON."}
        return write_result("send_prompt_empty", payload, log_dir)
    return send_text(message, dest=dest, channel_index=channel_index, confirm_send=confirm_send, password=password, prompt_password=prompt_password, log_dir=log_dir)


def gps_info(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, object]:
    profile = load_profile()
    result = _run(["meshtastic", *connection_args(profile), "--info"], timeout=25.0)
    payload = {"action": "gps_info", "display_name": DISPLAY_NAME, "profile": asdict(profile), "result": result, "note": "Use the connected Heltec or ESP32 Meshtastic node's firmware/GNSS status output.", "meshtastic_cli_available": meshtastic_cli_available()}
    return write_result("gps_info", payload, log_dir)


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Password-protected KoalaByte Meshtastic app")
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="Save local Meshtastic connection profile")
    setup.add_argument("--connection", choices=["serial", "tcp", "ble"], default="serial")
    setup.add_argument("--port", default=DEFAULT_SERIAL_PORT)
    setup.add_argument("--host", default="")
    setup.add_argument("--ble", default="")
    setup.add_argument("--label", default="KoalaByte Heltec Meshtastic Node")
    sub.add_parser("profile", help="Show saved/effective connection profile")
    sub.add_parser("send-prompt", help="Show menu-managed send prompt state")
    sub.add_parser("set-test-message", help="Set menu-managed test message and reset confirmation")
    sub.add_parser("set-checkin-message", help="Set menu-managed check-in message and reset confirmation")
    sub.add_parser("confirm-send-on", help="Turn menu-managed send confirmation on")
    sub.add_parser("confirm-send-off", help="Turn menu-managed send confirmation off")
    sub.add_parser("clear-send-prompt", help="Clear menu-managed send prompt state")
    sub.add_parser("compat", help="Show iPhone/Android and ESP32 Meshtastic compatibility notes")
    sub.add_parser("phone", help="Show iPhone/Android Meshtastic app pairing guide")
    sub.add_parser("esp32", help="Show ESP32 Meshtastic device connection guide")
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
        profile = MeshtasticProfile(args.connection, args.port, args.host, args.ble, args.label)
        print(json.dumps(save_profile(profile), indent=2, sort_keys=True))
        return 0
    if args.command == "profile":
        print(json.dumps(profile_status(), indent=2, sort_keys=True))
        return 0
    if args.command == "send-prompt":
        print(json.dumps(send_prompt_status(), indent=2, sort_keys=True))
        return 0
    if args.command == "set-test-message":
        print(json.dumps(set_send_message_preset("test"), indent=2, sort_keys=True))
        return 0
    if args.command == "set-checkin-message":
        print(json.dumps(set_send_message_preset("checkin"), indent=2, sort_keys=True))
        return 0
    if args.command == "confirm-send-on":
        print(json.dumps(set_send_confirm(True), indent=2, sort_keys=True))
        return 0
    if args.command == "confirm-send-off":
        print(json.dumps(set_send_confirm(False), indent=2, sort_keys=True))
        return 0
    if args.command == "clear-send-prompt":
        print(json.dumps(clear_send_prompt(), indent=2, sort_keys=True))
        return 0
    if args.command == "compat":
        print(json.dumps(compatibility_status(), indent=2, sort_keys=True))
        return 0
    if args.command == "phone":
        print(json.dumps(phone_pairing_guide(), indent=2, sort_keys=True))
        return 0
    if args.command == "esp32":
        print(json.dumps(esp32_device_guide(), indent=2, sort_keys=True))
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
