from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from .menu_ui import MenuItem

LOG_DIR = Path("logs/menu_actions")


@dataclass(frozen=True)
class CommandSpec:
    argv: Sequence[str]
    timeout: float = 45.0
    description: str = ""


SAFE_COMMANDS: Dict[str, CommandSpec] = {
    "koala_bluez_inventory": CommandSpec(["scripts/run_koala_bluez.py", "manifest"], description="BlueZ helper manifest"),
    "koala_bluez_status": CommandSpec(["scripts/run_koala_bluez.py", "inventory"], description="BlueZ local inventory"),
    "koala_bluez_scan": CommandSpec(["scripts/run_koala_bluez.py", "scan"], timeout=60.0, description="Bounded BlueZ discovery"),
    "koala_bluez_monitor": CommandSpec(["scripts/run_koala_bluez.py", "status"], description="BlueZ status check"),
    "koala_bluez_all_safe": CommandSpec(["scripts/run_koala_bluez.py", "all-safe"], timeout=90.0, description="BlueZ safe bundle"),
    "t114_bluez_controller_check": CommandSpec(["scripts/run_t114_bluez.py", "controller-check"], description="T114 HCI controller check"),
    "t114_bluez_all_safe": CommandSpec(["scripts/run_t114_bluez.py", "all-safe"], timeout=90.0, description="T114 BlueZ safe bundle"),
    "meshtastic_status": CommandSpec(["scripts/run_meshtastic_app.py", "status"], description="Meshtastic status"),
    "meshtastic_nodes": CommandSpec(["scripts/run_meshtastic_app.py", "nodes"], description="Meshtastic node table"),
    "didgeridoo": CommandSpec(["scripts/run_didgeridoo.py"], timeout=90.0, description="Didgeridoo Meshtastic status/nodes/GNSS bundle"),
    "greatwhite_status": CommandSpec(["scripts/run_gw.py", "status"], description="Greatwhite readiness"),
    "greatwhite_interfaces": CommandSpec(["scripts/run_gw.py", "interfaces"], description="Greatwhite local interfaces"),
    "nrf_sniffer_check": CommandSpec(["bash", "scripts/setup_nrf_sniffer_ble.sh", "--check-only"], description="nRF Sniffer host-side check"),
    "anteater": CommandSpec(["scripts/run_anteater.py", "--once"], timeout=90.0, description="AntEater passive risk triage"),
    "koala_kry": CommandSpec(["scripts/run_koala_kry.py", "--max-records", "25"], timeout=90.0, description="Koala Kry offline metadata replay"),
    "koala_kry_transmit_review": CommandSpec(["scripts/run_koala_kry.py", "--write-transmit-review", "--max-records", "25"], timeout=90.0, description="Koala Kry RF bench review; no RF sent"),
    "koala_kan_kommander": CommandSpec(["scripts/run_koala_kan_kommander.py", "status"], description="Koala Kan Kommander status"),
    "koala_konnect_t114_build_only": CommandSpec(["bash", "scripts/build_koala_konnect_t114.sh"], timeout=120.0, description="Koala Konnect T114 build check"),
    "koala_mode_switcher": CommandSpec(["scripts/select_t114_startup_mode.py", "--timeout", "10"], description="Choose T114 startup mode"),
    "koala_konnect_t114": CommandSpec(["scripts/select_t114_startup_mode.py", "--mode", "konnect"], description="Select Koala Konnect T114 startup mode"),
    "killerkoala_voice": CommandSpec(["scripts/run_killerkoala_voice.py", "status", "--xp", "100"], description="KillerKoala voice status"),
    "eucalyptus_mode": CommandSpec(["scripts/check_eucalyptus_cyberpet.py"], timeout=60.0, description="Eucalyptus Koalagotchi smoke/open check"),
    "location_password_status": CommandSpec(["scripts/run_location_password_gate.py", "status"], description="Protected gate status"),
    "location_password_setup": CommandSpec(["scripts/run_location_password_gate.py", "setup"], description="Protected gate setup"),
    "gnss_protected_fix": CommandSpec(["scripts/run_meshtastic_app.py", "gps"], description="Protected GNSS/status helper"),
}


def _artifact_name(command: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in command)[:72] or "menu_action"
    return LOG_DIR / f"{safe}_{int(time.time())}.json"


def _run_subprocess(spec: CommandSpec) -> dict[str, object]:
    argv = list(spec.argv)
    if argv and argv[0].endswith(".py"):
        argv = [sys.executable, *argv]
    started = time.time()
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=spec.timeout, check=False)
        return {
            "argv": argv,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-6000:],
            "stderr": completed.stderr[-6000:],
            "started_at": started,
            "ended_at": time.time(),
        }
    except FileNotFoundError as exc:
        return {"argv": argv, "returncode": 127, "stdout": "", "stderr": str(exc), "started_at": started, "ended_at": time.time()}
    except subprocess.TimeoutExpired as exc:
        return {"argv": argv, "returncode": 124, "stdout": str(exc.stdout or "")[-6000:], "stderr": "timeout", "started_at": started, "ended_at": time.time()}


def fallback_route(item: MenuItem) -> Path:
    path = _artifact_name(item.command)
    payload = {
        "timestamp": time.time(),
        "label": item.label,
        "command": item.command,
        "group": item.group,
        "status": "routed",
        "message": "No direct safe runner is registered yet for this command; selection was logged for follow-up implementation.",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def execute_menu_item(item: MenuItem) -> Path:
    spec = SAFE_COMMANDS.get(item.command)
    if spec is None:
        return fallback_route(item)
    result = _run_subprocess(spec)
    path = _artifact_name(item.command)
    payload = {
        "timestamp": time.time(),
        "label": item.label,
        "command": item.command,
        "group": item.group,
        "status": "success" if result.get("returncode") == 0 else "error",
        "runner_description": spec.description,
        "result": result,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def menu_handler(item: MenuItem) -> None:
    path = execute_menu_item(item)
    print(f"\n🌿 {item.label} executed/routed → {path}\n")
