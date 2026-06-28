from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

PROMPT_PATH = Path("logs/menu_prompts/action_prompt_state.json")

DEFAULT_STATE: dict[str, Any] = {
    "eucalyptus": {"gps_logging": True, "wigle_upload": False, "wigle_dry_run": True},
    "kruisin": {
        "gps_logging": True,
        "node_mesh": True,
        "esp32_port": "/dev/ttyACM1",
        "heltec_port": "/dev/ttyACM0",
        "wigle_upload": False,
        "wigle_dry_run": True,
    },
    "location_gate": {"menu_lab_unlock": False},
}


def _deepcopy_default() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_STATE))


def _write_result(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    root = PROMPT_PATH.parent
    root.mkdir(parents=True, exist_ok=True)
    artifact = root / f"{name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["artifact_path"] = str(artifact)
    return payload


def load_state() -> dict[str, Any]:
    state = _deepcopy_default()
    if PROMPT_PATH.exists():
        try:
            saved = json.loads(PROMPT_PATH.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                for section, values in saved.items():
                    if isinstance(values, dict):
                        state.setdefault(section, {}).update(values)
        except Exception as exc:
            state["load_error"] = str(exc)
    return state


def save_state(state: dict[str, Any]) -> dict[str, Any]:
    clean = _deepcopy_default()
    for section in ("eucalyptus", "kruisin", "location_gate"):
        clean[section].update(state.get(section, {}) if isinstance(state.get(section), dict) else {})
    clean["updated_at"] = time.time()
    clean["scope"] = "menu-managed UI state replacing shell prompt toggles for local KoalaByte actions"
    PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_PATH.write_text(json.dumps(clean, indent=2, sort_keys=True), encoding="utf-8")
    return {"saved": True, "path": str(PROMPT_PATH), "state": clean}


def prompt_status() -> dict[str, Any]:
    return _write_result("prompt_status", {"status": "MENU_PROMPT_STATE_READY", "path": str(PROMPT_PATH), "state": load_state()})


def set_bool(section: str, key: str, enabled: bool) -> dict[str, Any]:
    state = load_state()
    state.setdefault(section, {})[key] = bool(enabled)
    saved = save_state(state)
    return _write_result(f"{section}_{key}_{'on' if enabled else 'off'}", {"status": "MENU_PROMPT_VALUE_SET", "section": section, "key": key, "enabled": bool(enabled), **saved})


def set_kruisin_default_ports() -> dict[str, Any]:
    state = load_state()
    kruisin = state.setdefault("kruisin", {})
    kruisin["esp32_port"] = "/dev/ttyACM1"
    kruisin["heltec_port"] = "/dev/ttyACM0"
    saved = save_state(state)
    return _write_result("kruisin_default_ports", {"status": "KRUISIN_DEFAULT_PORTS_SET", **saved})


def apply_location_gate_env() -> dict[str, Any]:
    state = load_state().get("location_gate", {})
    enabled = bool(state.get("menu_lab_unlock", False))
    if enabled:
        os.environ["KOALABYTE_LOCATION_UNLOCKED"] = "1"
        os.environ["KOALABYTE_AUTHORIZED_LOCATION_LOGGING"] = "1"
    else:
        os.environ.pop("KOALABYTE_LOCATION_UNLOCKED", None)
        os.environ.pop("KOALABYTE_AUTHORIZED_LOCATION_LOGGING", None)
    return {"menu_lab_unlock": enabled}


def apply_eucalyptus_env() -> dict[str, Any]:
    state = load_state().get("eucalyptus", {})
    if bool(state.get("gps_logging", True)):
        os.environ["KOALABYTE_EUCALYPTUS_GPS_LOGGING"] = "1"
    else:
        os.environ.pop("KOALABYTE_EUCALYPTUS_GPS_LOGGING", None)
    if bool(state.get("wigle_upload", False)):
        os.environ["KOALABYTE_EUCALYPTUS_WIGLE_UPLOAD"] = "1"
    else:
        os.environ.pop("KOALABYTE_EUCALYPTUS_WIGLE_UPLOAD", None)
    apply_location_gate_env()
    return {"eucalyptus": state, "location_gate": load_state().get("location_gate", {})}


def apply_kruisin_env() -> dict[str, Any]:
    state = load_state().get("kruisin", {})
    os.environ["KOALA_KOMBAT_NODE_MESH"] = "1" if bool(state.get("node_mesh", True)) else "0"
    os.environ["KOALA_KOMBAT_GPS_LOGGING"] = "1" if bool(state.get("gps_logging", True)) else "0"
    os.environ["KOALA_KOMBAT_ESP32_PORT"] = str(state.get("esp32_port") or "/dev/ttyACM1")
    os.environ["KOALA_KOMBAT_HELTEC_PORT"] = str(state.get("heltec_port") or "/dev/ttyACM0")
    if bool(state.get("wigle_upload", False)):
        os.environ["KOALA_KOMBAT_WIGLE_UPLOAD"] = "1"
    else:
        os.environ.pop("KOALA_KOMBAT_WIGLE_UPLOAD", None)
    apply_location_gate_env()
    return {"kruisin": state, "location_gate": load_state().get("location_gate", {})}


def eucalyptus_dry_run_enabled() -> bool:
    return bool(load_state().get("eucalyptus", {}).get("wigle_dry_run", True))


def kruisin_dry_run_enabled() -> bool:
    return bool(load_state().get("kruisin", {}).get("wigle_dry_run", True))
