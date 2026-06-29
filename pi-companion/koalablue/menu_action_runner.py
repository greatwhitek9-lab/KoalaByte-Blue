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


def _prompt(command: str) -> dict[str, Any]:
    from . import menu_prompt_state
    handlers: dict[str, Callable[[], Any]] = {
        "prompt_state_status": menu_prompt_state.prompt_status,
        "eucalyptus_prompt_status": menu_prompt_state.prompt_status,
        "eucalyptus_gps_on": lambda: menu_prompt_state.set_bool("eucalyptus", "gps_logging", True),
        "eucalyptus_gps_off": lambda: menu_prompt_state.set_bool("eucalyptus", "gps_logging", False),
        "eucalyptus_wigle_dry_run_on": lambda: menu_prompt_state.set_bool("eucalyptus", "wigle_dry_run", True),
        "eucalyptus_wigle_dry_run_off": lambda: menu_prompt_state.set_bool("eucalyptus", "wigle_dry_run", False),
        "eucalyptus_wigle_upload_on": lambda: menu_prompt_state.set_bool("eucalyptus", "wigle_upload", True),
        "eucalyptus_wigle_upload_off": lambda: menu_prompt_state.set_bool("eucalyptus", "wigle_upload", False),
        "kruisin_prompt_status": menu_prompt_state.prompt_status,
        "kruisin_gps_on": lambda: menu_prompt_state.set_bool("kruisin", "gps_logging", True),
        "kruisin_gps_off": lambda: menu_prompt_state.set_bool("kruisin", "gps_logging", False),
        "kruisin_nodes_on": lambda: menu_prompt_state.set_bool("kruisin", "node_mesh", True),
        "kruisin_nodes_off": lambda: menu_prompt_state.set_bool("kruisin", "node_mesh", False),
        "kruisin_default_ports": menu_prompt_state.set_kruisin_default_ports,
        "kruisin_wigle_dry_run_on": lambda: menu_prompt_state.set_bool("kruisin", "wigle_dry_run", True),
        "kruisin_wigle_dry_run_off": lambda: menu_prompt_state.set_bool("kruisin", "wigle_dry_run", False),
        "kruisin_wigle_upload_on": lambda: menu_prompt_state.set_bool("kruisin", "wigle_upload", True),
        "kruisin_wigle_upload_off": lambda: menu_prompt_state.set_bool("kruisin", "wigle_upload", False),
        "location_gate_unlock_on": lambda: menu_prompt_state.set_bool("location_gate", "menu_lab_unlock", True),
        "location_gate_unlock_off": lambda: menu_prompt_state.set_bool("location_gate", "menu_lab_unlock", False),
    }
    handler = handlers.get(command)
    if handler is None:
        return {"status": "PROMPT_ACTION_RECORDED", "command": command}
    return handler()


def _bluez_lab_scope(command: str) -> dict[str, Any]:
    from . import bluez_lab_scope
    if command == "bluez_lab_scope_status":
        return bluez_lab_scope.scope_status()
    if command == "bluez_lab_owned_on":
        return bluez_lab_scope.set_owned(True)
    if command == "bluez_lab_owned_off":
        return bluez_lab_scope.set_owned(False)
    if command == "bluez_lab_scope_clear":
        return bluez_lab_scope.clear_scope()
    return {"status": "BLUEZ_LAB_SCOPE_ACTION_RECORDED", "command": command}


def _eucalyptus(command: str) -> dict[str, Any]:
    from . import menu_prompt_state
    from .eucalyptus_wigle import control_status, upload_to_wigle
    applied = menu_prompt_state.apply_eucalyptus_env()
    action = command.split(" ", 1)[1] if " " in command else "status"
    if action in {"wigle-upload", "upload"}:
        result = upload_to_wigle(dry_run=menu_prompt_state.eucalyptus_dry_run_enabled())
    else:
        result = control_status(action)
    if isinstance(result, dict):
        result["menu_prompt_state"] = applied
    return result


def _kruisin(command: str) -> dict[str, Any]:
    from . import menu_prompt_state
    from .koala_kombat_kruisin import control
    applied = menu_prompt_state.apply_kruisin_env()
    action = command.split(" ", 1)[1] if " " in command else "status"
    result = control(action, dry_run=menu_prompt_state.kruisin_dry_run_enabled() if action in {"wigle-upload", "upload"} else False)
    if isinstance(result, dict):
        result["menu_prompt_state"] = applied
    return result


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
        from . import menu_prompt_state
        menu_prompt_state.apply_location_gate_env()
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
        from . import menu_prompt_state
        menu_prompt_state.apply_location_gate_env()
        return meshtastic_app.send_from_prompt(prompt_password=False)
    return {"status": "MESHTASTIC_ACTION_RECORDED", "command": command}


def _location_gate() -> dict[str, Any]:
    from . import menu_prompt_state
    applied = menu_prompt_state.apply_location_gate_env()
    from .location_password_gate import PASSWORD_FILE, UNLOCK_ENV, password_exists
    return {"status": "LOCATION_GATE_STATUS_READY", "configured": password_exists(), "unlocked": os.environ.get(UNLOCK_ENV) in {"1", "true", "TRUE", "yes", "YES"}, "path": str(PASSWORD_FILE), "menu_prompt_state": applied}


def _protected_bluez(command: str) -> dict[str, Any]:
    from . import bluez_lab_scope, bluez_protected_lab
    scope = bluez_lab_scope.apply_env()
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
        return {"status": "PROTECTED_BLUEZ_ACTION_RECORDED", "command": command, "bluez_lab_scope": scope}
    result = asdict(handler())
    result["bluez_lab_scope"] = scope
    return result


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
    if command in {"shutdown_confirm", "power_toggle", "power_on_off"}:
        payload = {"status": "SHUTDOWN_REQUESTED", "command": "sudo shutdown -h now", "source": "front_panel_power_or_menu"}
        if os.getenv("KOALABYTE_MENU_SHUTDOWN_DRY_RUN", "0") == "1":
            payload["status"] = "SHUTDOWN_DRY_RUN"
            return payload
        try:
            subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        except Exception as exc:
            payload["status"] = "SHUTDOWN_FAILED"
            payload["error"] = str(exc)
        return payload
    if command in {"reset_confirm", "reset", "reboot", "reset_reboot"}:
        payload = {"status": "RESET_REBOOT_REQUESTED", "command": "sudo reboot", "source": "front_panel_reset_or_menu"}
        if os.getenv("KOALABYTE_MENU_RESET_DRY_RUN", "0") == "1":
            payload["status"] = "RESET_REBOOT_DRY_RUN"
            return payload
        try:
            subprocess.Popen(["sudo", "reboot"])
        except Exception as exc:
            payload["status"] = "RESET_REBOOT_FAILED"
            payload["error"] = str(exc)
        return payload
    return {"status": "SYSTEM_ACTION_RECORDED"}


def run_automated_menu_action(command: str, label: str = "", group: str = "") -> dict[str, Any]:
    try:
        if command.startswith("submenu:"):
            return _ok(command, label, {"status": "SUBMENU_NAVIGATION_ONLY", "target": command.split(":", 1)[1]})
        if command.startswith("status:"):
            return _ok(command, label, _status_row(command), "AUTOMATED_STATUS_COMPLETE")
        if command in {"prompt_state_status", "eucalyptus_prompt_status", "eucalyptus_gps_on", "eucalyptus_gps_off", "eucalyptus_wigle_dry_run_on", "eucalyptus_wigle_dry_run_off", "eucalyptus_wigle_upload_on", "eucalyptus_wigle_upload_off", "kruisin_prompt_status", "kruisin_gps_on", "kruisin_gps_off", "kruisin_nodes_on", "kruisin_nodes_off", "kruisin_default_ports", "kruisin_wigle_dry_run_on", "kruisin_wigle_dry_run_off", "kruisin_wigle_upload_on", "kruisin_wigle_upload_off", "location_gate_unlock_on", "location_gate_unlock_off"}:
            return _ok(command, label, _prompt(command))
        if command.startswith("bluez_lab_"):
            return _ok(command, label, _bluez_lab_scope(command))
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
        if command in {"killerkoala_voice", "buttons", "level/status", "wake killerkoala", "settings", "koala_mode_switcher", "shutdown_confirm", "power_toggle", "power_on_off", "reset_confirm", "reset", "reboot", "reset_reboot"}:
            return _ok(command, label, _system_status(command))
        if command == "quit":
            return _ok(command, label, {"status": "QUIT_REQUEST_RECORDED"})
        return _ok(command, label, {"status": "AUTOMATED_PLACEHOLDER_COMPLETE", "command": command, "group": group})
    except Exception as exc:
        return _error(command, label, exc)
