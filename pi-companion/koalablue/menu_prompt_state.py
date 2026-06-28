from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

PROMPT_PATH = Path("logs/menu_prompts/action_prompt_state.json")
WIGLE_CREDENTIAL_PATH = Path("logs/security/wigle_credentials.json")
BOOT_WIGLE_CREDENTIAL_PATHS = [Path("/boot/firmware/koalabyte_wigle.json"), Path("/boot/koalabyte_wigle.json")]

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
    return _write_result("prompt_status", {"status": "MENU_PROMPT_STATE_READY", "path": str(PROMPT_PATH), "state": load_state(), "wigle_profile": wigle_profile_summary()})


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


def _normalise_wigle_record(data: dict[str, Any]) -> dict[str, str]:
    api_name = str(data.get("api_name") or data.get("name") or data.get("WIGLE_API_NAME") or "").strip()
    api_token = str(data.get("api_token") or data.get("token") or data.get("WIGLE_API_TOKEN") or "").strip()
    return {"api_name": api_name, "api_token": api_token}


def load_wigle_credentials(path: Path = WIGLE_CREDENTIAL_PATH) -> dict[str, str]:
    if not path.exists():
        return {"api_name": "", "api_token": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _normalise_wigle_record(data if isinstance(data, dict) else {})
    except Exception:
        return {"api_name": "", "api_token": ""}


def wigle_profile_summary() -> dict[str, Any]:
    creds = load_wigle_credentials()
    return {
        "path": str(WIGLE_CREDENTIAL_PATH),
        "configured": bool(creds.get("api_name") and creds.get("api_token")),
        "boot_import_paths": [str(path) for path in BOOT_WIGLE_CREDENTIAL_PATHS],
        "credential_file_format": {"api_name": "<WiGLE API name>", "api_token": "<WiGLE API token>"},
    }


def wigle_profile_status() -> dict[str, Any]:
    return _write_result("wigle_profile_status", {"status": "WIGLE_PROFILE_READY" if wigle_profile_summary()["configured"] else "WIGLE_PROFILE_NOT_CONFIGURED", "wigle_profile": wigle_profile_summary()})


def import_wigle_profile() -> dict[str, Any]:
    for source in BOOT_WIGLE_CREDENTIAL_PATHS:
        if not source.exists():
            continue
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            creds = _normalise_wigle_record(data if isinstance(data, dict) else {})
            if not creds["api_name"] or not creds["api_token"]:
                continue
            WIGLE_CREDENTIAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            WIGLE_CREDENTIAL_PATH.write_text(json.dumps({"api_name": creds["api_name"], "api_token": creds["api_token"], "imported_at": time.time(), "source": str(source)}, indent=2, sort_keys=True), encoding="utf-8")
            try:
                WIGLE_CREDENTIAL_PATH.chmod(0o600)
            except Exception:
                pass
            return _write_result("wigle_profile_imported", {"status": "WIGLE_PROFILE_IMPORTED", "source": str(source), "path": str(WIGLE_CREDENTIAL_PATH), "configured": True})
        except Exception as exc:
            return _write_result("wigle_profile_import_failed", {"status": "WIGLE_PROFILE_IMPORT_FAILED", "source": str(source), "error": str(exc)})
    return _write_result("wigle_profile_import_missing", {"status": "WIGLE_PROFILE_IMPORT_NOT_FOUND", "expected_paths": [str(path) for path in BOOT_WIGLE_CREDENTIAL_PATHS], "format": {"api_name": "<WiGLE API name>", "api_token": "<WiGLE API token>"}})


def apply_wigle_env() -> dict[str, Any]:
    creds = load_wigle_credentials()
    if creds.get("api_name") and creds.get("api_token"):
        os.environ.setdefault("WIGLE_API_NAME", creds["api_name"])
        os.environ.setdefault("WIGLE_API_TOKEN", creds["api_token"])
    return {"configured": bool(creds.get("api_name") and creds.get("api_token")), "path": str(WIGLE_CREDENTIAL_PATH)}


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
    location = apply_location_gate_env()
    wigle = apply_wigle_env()
    return {"eucalyptus": state, "location_gate": location, "wigle_profile": wigle}


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
    location = apply_location_gate_env()
    wigle = apply_wigle_env()
    return {"kruisin": state, "location_gate": location, "wigle_profile": wigle}


def eucalyptus_dry_run_enabled() -> bool:
    return bool(load_state().get("eucalyptus", {}).get("wigle_dry_run", True))


def kruisin_dry_run_enabled() -> bool:
    return bool(load_state().get("kruisin", {}).get("wigle_dry_run", True))
