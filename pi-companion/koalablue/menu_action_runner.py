from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable

OUTPUT_DIR = Path("logs/menu_actions")
STATUS_PATH = OUTPUT_DIR / "automated_menu_action_status.json"


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _write_json(name: str, payload: dict[str, Any]) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)[:72] or "action"
    path = OUTPUT_DIR / f"{safe}_{int(time.time())}.json"
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")
    STATUS_PATH.write_text(json.dumps({"status": payload.get("status"), "command": name, "artifact_path": str(path), "updated_at": time.time()}, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def _ok(command: str, label: str, result: Any, status: str = "AUTOMATED_ACTION_COMPLETE") -> dict[str, Any]:
    payload = {"status": status, "command": command, "label": label, "manual_prompt_required": False, "selected_from_menu": True, "voice_command_compatible": True, "result": _jsonable(result), "timestamp": time.time()}
    payload["artifact_path"] = _write_json(command, payload)
    return payload


def _error(command: str, label: str, exc: Exception) -> dict[str, Any]:
    payload = {"status": "AUTOMATED_ACTION_SKIPPED", "command": command, "label": label, "manual_prompt_required": False, "voice_command_compatible": True, "error": str(exc), "timestamp": time.time()}
    payload["artifact_path"] = _write_json(command, payload)
    return payload


def _lab_action(command: str) -> dict[str, Any]:
    from .authorized_lab_actions import AuthorizedLabActions
    result = AuthorizedLabActions().run(command, authorized=True, context={"source": "menu_or_voice_select", "manual_prompt_required": False})
    return asdict(result)


def _status_row(command: str) -> dict[str, Any]:
    from .t114_menu_status import status_label_description
    label, description = status_label_description(command)
    return {"status": "STATUS_ROW_CHECKED", "status_label": label, "description": description}


def _ble_scan_summary(command: str) -> dict[str, Any]:
    from .bluez_tools import all_safe, scan, status
    if command == "scan":
        return asdict(scan(duration_seconds=10))
    if command == "summary":
        return {"runs": [_jsonable(item) for item in all_safe(duration_seconds=8)], "summary": "Local Bluetooth inventory, status, and bounded discovery collected."}
    return asdict(status())


def _koala_kapture() -> dict[str, Any]:
    from .koala_kapture import KoalaKaptureConfig, KoalaKaptureRecorder
    cfg = KoalaKaptureConfig(duration_seconds=float(os.getenv("KOALABYTE_MENU_KAPTURE_SECONDS", "12")), scan_window_seconds=4.0, max_records=300)
    return asdict(asyncio.run(KoalaKaptureRecorder(cfg).record()))


def _koala_kry(command: str = "koala_kry") -> dict[str, Any]:
    from . import koala_kry

    handlers: dict[str, Callable[[], Any]] = {
        "koala_kry": lambda: koala_kry.run_from_prompt(review_only=False),
        "koala_kry_run_replay": lambda: koala_kry.run_from_prompt(review_only=False),
        "koala_kry_transmit_review": lambda: koala_kry.run_from_prompt(review_only=True),
        "koala_kry_run_review": lambda: koala_kry.run_from_prompt(review_only=True),
        "koala_kry_prompt_status": koala_kry.prompt_status,
        "koala_kry_use_latest_capture": koala_kry.set_latest_capture,
        "koala_kry_speed_live": lambda: koala_kry.set_speed_preset("live"),
        "koala_kry_speed_fast": lambda: koala_kry.set_speed_preset("fast"),
        "koala_kry_speed_instant": lambda: koala_kry.set_speed_preset("instant"),
        "koala_kry_limit_50": lambda: koala_kry.set_record_limit(50),
        "koala_kry_limit_200": lambda: koala_kry.set_record_limit(200),
        "koala_kry_limit_all": lambda: koala_kry.set_record_limit(None),
        "koala_kry_rf_review_on": lambda: koala_kry.set_rf_review(True),
        "koala_kry_rf_review_off": lambda: koala_kry.set_rf_review(False),
        "koala_kry_lab_ack_on": lambda: koala_kry.set_lab_ack(True),
        "koala_kry_owned_ack_on": lambda: koala_kry.set_owned_ack(True),
        "koala_kry_clear_prompt": koala_kry.clear_prompt,
    }
    handler = handlers.get(command)
    if handler is None:
        return {"status": "KOALA_KRY_ACTION_RECORDED", "command": command}
    return handler()


def _urban_poaching() -> dict[str, Any]:
    from .urban_poaching import UrbanPoachingConfig, UrbanPoachingGame
    cfg = UrbanPoachingConfig(rounds=3, scan_seconds=3.0)
    return asdict(asyncio.run(UrbanPoachingGame(cfg).play()))


def _koala_kan() -> dict[str, Any]:
    from .koala_kan_kommander import inventory, manifest, report, status
    return {"manifest": manifest(), "inventory": inventory(), "status": status(), "report": report()}


def _defense_guard() -> dict[str, Any]:
    try:
        from .ble_defense_guard import load_monitor_settings
        settings = load_monitor_settings()
    except Exception as exc:
        settings = {"note": "defense guard settings unavailable", "error": str(exc)}
    return {"status": "DEFENSE_GUARD_SETTINGS_READY", "settings": settings}


def _ear_tag_plan() -> dict[str, Any]:
    try:
        from .ear_tag_tx_lab import write_ear_tag_tx_lab_plan
        path = write_ear_tag_tx_lab_plan(Path("logs/ear_tag_tx_lab"))
        return {"status": "LAB_BEACON_PLAN_READY", "plan_path": str(path)}
    except Exception:
        return {"status": "LAB_BEACON_PLAN_READY", "result": _lab_action("lab_beacon_plan")}


def _boomerang_export() -> dict[str, Any]:
    from .camera_awareness_logger import LOG_ROOT, build_summary, export_csv, export_json, load_observations
    root = Path(LOG_ROOT)
    observations = load_observations(root)
    return {"status": "BOOMERANG_EXPORT_READY", "records": len(observations), "summary": build_summary(observations), "json_path": str(export_json(observations, root)), "csv_path": str(export_csv(observations, root))}


def _eucalyptus(command: str) -> dict[str, Any]:
    from .eucalyptus_wigle import control_status
    action = command.split(" ", 1)[1] if " " in command else "status"
    return control_status(action)


def _kruisin(command: str) -> dict[str, Any]:
    from .koala_kombat_kruisin import control
    os.environ.setdefault("KOALA_KOMBAT_NODE_MESH", "1")
    os.environ.setdefault("KOALA_KOMBAT_ESP32_PORT", "/dev/ttyACM1")
    os.environ.setdefault("KOALA_KOMBAT_HELTEC_PORT", "/dev/ttyACM0")
    os.environ.setdefault("KOALA_KOMBAT_GPS_LOGGING", "1")
    action = command.split(" ", 1)[1] if " " in command else "status"
    return control(action)


def _t114_action(command: str) -> dict[str, Any]:
    if command in {"t114_primary_ble_scan", "t114_bluez_status", "t114_primary_status"}:
        from .t114_bluez import run_wrapped_bluez
        action = "scan" if command == "t114_primary_ble_scan" else "status"
        seconds = 30 if action == "scan" else 10
        return asdict(run_wrapped_bluez(action, duration_seconds=seconds))
    if command == "t114_ble_tx_status":
        from .t114_bluez import run_wrapped_bluez
        return asdict(run_wrapped_bluez("tx-status", duration_seconds=5))
    if command in {"t114_primary_controller_check", "t114_bluez_controller_check"}:
        from .t114_bluez import check_controller
        return asdict(check_controller())
    if command in {"t114_primary_gnss_fix", "gnss_current_fix"}:
        from .gnss_location import current_fix, fix_to_dict
        return {"status": "GNSS_FIX_READ", "fix": fix_to_dict(current_fix(authorized=None, prompt=False)), "source_priority": "heltec-t114-gnss"}
    return {"status": "T114_ACTION_RECORDED", "command": command}


def _meshtastic(command: str) -> dict[str, Any]:
    from . import meshtastic_app
    if command in {"meshtastic_app", "meshtastic_profile"}:
        return meshtastic_app.profile_status()
    if command == "meshtastic_send_prompt":
        return meshtastic_app.send_prompt_status()
    if command == "meshtastic_set_test_message":
        return meshtastic_app.set_send_message_preset("test")
    if command == "meshtastic_set_checkin_message":
        return meshtastic_app.set_send_message_preset("checkin")
    if command == "meshtastic_confirm_send_on":
        return meshtastic_app.set_send_confirm(True)
    if command == "meshtastic_confirm_send_off":
        return meshtastic_app.set_send_confirm(False)
    if command == "meshtastic_clear_send_prompt":
        return meshtastic_app.clear_send_prompt()
    if command == "meshtastic_compatibility":
        return meshtastic_app.compatibility_status()
    if command == "meshtastic_phone_pairing":
        return meshtastic_app.phone_pairing_guide()
    if command == "meshtastic_esp32_device":
        return meshtastic_app.esp32_device_guide()
    if command == "meshtastic_setup_serial":
        return meshtastic_app.setup_serial()
    if command == "meshtastic_setup_tcp":
        return meshtastic_app.setup_tcp()
    if command == "meshtastic_setup_ble":
        return meshtastic_app.setup_ble()
    if command == "meshtastic_status":
        return meshtastic_app.status()
    if command == "meshtastic_nodes":
        return meshtastic_app.nodes()
    if command == "meshtastic_gps":
        return meshtastic_app.gps_info()
    if command == "meshtastic_listen":
        return meshtastic_app.listen(seconds=int(os.getenv("KOALABYTE_MESHTASTIC_LISTEN_SECONDS", "30")), prompt_password=False)
    if command == "meshtastic_send_gate":
        return meshtastic_app.send_from_prompt(prompt_password=False)
    return {"status": "MESHTASTIC_ACTION_RECORDED", "command": command}


def _location_gate() -> dict[str, Any]:
    from .location_password_gate import PASSWORD_FILE, UNLOCK_ENV, password_exists
    return {"status": "LOCATION_GATE_STATUS_READY", "configured": password_exists(), "unlocked": os.environ.get(UNLOCK_ENV) in {"1", "true", "TRUE", "yes", "YES"}, "path": str(PASSWORD_FILE)}


def _protected_bluez(command: str) -> dict[str, Any]:
    from . import bluez_protected_lab
    handlers: dict[str, Callable[[], Any]] = {
        "koala_bluez_info": bluez_protected_lab.protected_target_info,
        "koala_bluez_services": bluez_protected_lab.protected_target_services,
        "koala_bluez_gatt_readiness": bluez_protected_lab.protected_gatt_readiness,
        "bluez_outback_radio_ledger": bluez_protected_lab.outback_radio_ledger,
        "bluez_classic_track_finder": bluez_protected_lab.classic_track_finder,
        "bluez_treehouse_rfcomm_wiremap": bluez_protected_lab.treehouse_rfcomm_wiremap,
        "bluez_pouch_link_echo": bluez_protected_lab.pouch_link_echo,
        "bluez_gumnut_gatt_ghostmap": bluez_protected_lab.gumnut_gatt_ghostmap,
        "bluez_platypus_bt_proxy": bluez_protected_lab.platypus_bt_proxy,
    }
    handler = handlers.get(command)
    if handler is None:
        return {"status": "PROTECTED_BLUEZ_ACTION_RECORDED", "command": command}
    return asdict(handler())


def _bluez_wrapper(command: str) -> dict[str, Any]:
    from .bluez_tools import all_safe, inventory, module_manifest, monitor, scan, status
    if command == "koala_bluez_manifest":
        return asdict(module_manifest())
    if command == "koala_bluez_inventory":
        return asdict(inventory())
    if command == "koala_bluez_status":
        return asdict(status())
    if command == "koala_bluez_scan":
        return asdict(scan(duration_seconds=15))
    if command == "koala_bluez_monitor":
        return asdict(monitor(duration_seconds=20))
    if command == "koala_bluez_all_safe":
        return {"runs": [_jsonable(item) for item in all_safe(duration_seconds=15)]}
    return {"status": "BLUEZ_WRAPPER_ACTION_RECORDED", "command": command}


def _system_status(command: str) -> dict[str, Any]:
    if command == "buttons":
        return {"status": "BUTTON_CHECK_READY", "note": "GPIO button manager is loaded by the menu runner when available."}
    if command == "level/status":
        state_path = Path("logs/killerkoala/xp_state.json")
        if state_path.exists():
            return json.loads(state_path.read_text(encoding="utf-8"))
        return {"xp": 0, "rank": "Noob", "status": "XP_STATE_EMPTY"}
    if command == "wake killerkoala":
        return {"status": "WAKE_WORD_TEST_RECORDED", "wake_word": "killerkoala"}
    if command == "settings":
        return {"status": "SETTINGS_STATUS_READY", "config_hint": "pi-companion/config.default.json"}
    if command == "killerkoala_voice":
        from .killerkoala_voice_control import module_manifest
        return module_manifest()
    if command == "koala_mode_switcher":
        return {"status": "MODE_SWITCHER_STATUS_READY", "note": "Legacy dongle mode package helper is selectable without extra prompt."}
    if command == "shutdown_confirm":
        payload = {"status": "SHUTDOWN_REQUESTED", "command": "sudo shutdown -h now"}
        if os.getenv("KOALABYTE_MENU_SHUTDOWN_DRY_RUN", "0") == "1":
            payload["status"] = "SHUTDOWN_DRY_RUN"
            return payload
        try:
            subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        except Exception as exc:
            payload["status"] = "SHUTDOWN_FAILED"
            payload["error"] = str(exc)
        return payload
    return {"status": "SYSTEM_ACTION_RECORDED"}


def run_automated_menu_action(command: str, label: str = "", group: str = "") -> dict[str, Any]:
    try:
        if command.startswith("submenu:"):
            return _ok(command, label, {"status": "SUBMENU_NAVIGATION_ONLY", "target": command.split(":", 1)[1]})
        if command.startswith("status:"):
            return _ok(command, label, _status_row(command), "AUTOMATED_STATUS_COMPLETE")
        if command.startswith("eucalyptus ") or command == "eucalyptus_mode":
            return _ok(command, label, _eucalyptus("eucalyptus status" if command == "eucalyptus_mode" else command))
        if command.startswith("kruisin "):
            return _ok(command, label, _kruisin(command))
        if command in {"scan", "summary", "show"}:
            return _ok(command, label, _ble_scan_summary(command))
        if command.startswith("koala_bluez_") or command in {"bluez_outback_radio_ledger", "bluez_classic_track_finder", "bluez_treehouse_rfcomm_wiremap", "bluez_pouch_link_echo", "bluez_gumnut_gatt_ghostmap", "bluez_platypus_bt_proxy"}:
            if command in {"koala_bluez_manifest", "koala_bluez_inventory", "koala_bluez_status", "koala_bluez_scan", "koala_bluez_monitor", "koala_bluez_all_safe"}:
                return _ok(command, label, _bluez_wrapper(command))
            return _ok(command, label, _protected_bluez(command))
        if command.startswith("t114_") or command == "gnss_current_fix":
            return _ok(command, label, _t114_action(command))
        if command == "meshtastic_app" or command.startswith("meshtastic_"):
            return _ok(command, label, _meshtastic(command))
        if command == "location_gate_status":
            return _ok(command, label, _location_gate())
        if command == "koala_kapture":
            return _ok(command, label, _koala_kapture())
        if command == "koala_kry" or command.startswith("koala_kry_"):
            return _ok(command, label, _koala_kry(command))
        if command == "boomerang":
            return _ok(command, label, _boomerang_export())
        if command in {"authorized_ble_inventory", "gatt_readiness_checklist", "pairing_security_review", "lab_beacon_plan", "packet_capture_notes", "defensive_report", "report", "restricted_placeholder"}:
            return _ok(command, label, _lab_action("defensive_report" if command == "report" else command))
        if command == "koala_kan_kommander":
            return _ok(command, label, _koala_kan())
        if command == "urban_poaching":
            return _ok(command, label, _urban_poaching())
        if command == "thats_not_a_knife":
            return _ok(command, label, _defense_guard())
        if command == "anteater":
            from .anteater import run_once
            return _ok(command, label, asdict(run_once(scan_seconds=12.0)))
        if command in {"ear_tag", "ear_tag_tx_lab"}:
            return _ok(command, label, _ear_tag_plan())
        if command in {"killerkoala_voice", "buttons", "level/status", "wake killerkoala", "settings", "koala_mode_switcher", "shutdown_confirm"}:
            return _ok(command, label, _system_status(command))
        if command == "quit":
            return _ok(command, label, {"status": "QUIT_REQUEST_RECORDED"})
        return _ok(command, label, {"status": "AUTOMATED_PLACEHOLDER_COMPLETE", "command": command, "group": group})
    except Exception as exc:
        return _error(command, label, exc)
