from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

OUTPUT_DIR = Path("logs/menu_actions")
MANIFEST_PATH = OUTPUT_DIR / "menu_actionability_manifest.json"
STATUS_PATH = OUTPUT_DIR / "menu_actionability_status.json"
REPO_ROOT = Path(__file__).resolve().parents[2]

PROMPT_COMMANDS = {
    "prompt_state_status",
    "eucalyptus_prompt_status",
    "eucalyptus_gps_on",
    "eucalyptus_gps_off",
    "eucalyptus_wigle_dry_run_on",
    "eucalyptus_wigle_dry_run_off",
    "eucalyptus_wigle_upload_on",
    "eucalyptus_wigle_upload_off",
    "kruisin_prompt_status",
    "kruisin_gps_on",
    "kruisin_gps_off",
    "kruisin_nodes_on",
    "kruisin_nodes_off",
    "kruisin_default_ports",
    "kruisin_wigle_dry_run_on",
    "kruisin_wigle_dry_run_off",
    "kruisin_wigle_upload_on",
    "kruisin_wigle_upload_off",
    "location_gate_unlock_on",
    "location_gate_unlock_off",
}

EUCALYPTUS_COMMANDS = {
    "eucalyptus status",
    "eucalyptus start",
    "eucalyptus stop",
    "eucalyptus restart",
    "eucalyptus gps-trail",
    "eucalyptus upload-status",
    "eucalyptus wigle-upload",
    "eucalyptus_mode",
}

KRUISIN_COMMANDS = {
    "kruisin status",
    "kruisin wifi-survey",
    "kruisin ble-survey",
    "kruisin survey",
    "kruisin gps-status",
    "kruisin wigle-upload",
}

BLUEZ_SCOPE_COMMANDS = {
    "bluez_lab_scope_status",
    "bluez_lab_owned_on",
    "bluez_lab_owned_off",
    "bluez_lab_scope_clear",
}

BLUEZ_WRAPPER_COMMANDS = {
    "koala_bluez_manifest",
    "koala_bluez_inventory",
    "koala_bluez_status",
    "koala_bluez_scan",
    "koala_bluez_monitor",
    "koala_bluez_all_safe",
}

PROTECTED_BLUEZ_COMMANDS = {
    "koala_bluez_info",
    "koala_bluez_services",
    "koala_bluez_gatt_readiness",
    "bluez_outback_radio_ledger",
    "bluez_classic_track_finder",
    "bluez_treehouse_rfcomm_wiremap",
    "bluez_pouch_link_echo",
    "bluez_gumnut_gatt_ghostmap",
    "bluez_platypus_bt_proxy",
}

T114_COMMANDS = {
    "t114_primary_ble_scan",
    "t114_bluez_status",
    "t114_primary_status",
    "t114_ble_tx_status",
    "t114_primary_controller_check",
    "t114_bluez_controller_check",
    "t114_primary_gnss_fix",
    "gnss_current_fix",
}

MESHTASTIC_COMMANDS = {
    "meshtastic_app",
    "meshtastic_profile",
    "meshtastic_send_prompt",
    "meshtastic_send_prompt_status",
    "meshtastic_set_test_message",
    "meshtastic_set_checkin_message",
    "meshtastic_confirm_send_on",
    "meshtastic_confirm_on",
    "meshtastic_confirm_send_off",
    "meshtastic_confirm_off",
    "meshtastic_clear_send_prompt",
    "meshtastic_clear_send",
    "meshtastic_compatibility",
    "meshtastic_compat",
    "meshtastic_phone_pairing",
    "meshtastic_esp32_device",
    "meshtastic_esp32_link",
    "meshtastic_setup_serial",
    "meshtastic_use_serial",
    "meshtastic_setup_tcp",
    "meshtastic_use_tcp",
    "meshtastic_setup_ble",
    "meshtastic_use_ble",
    "meshtastic_status",
    "meshtastic_nodes",
    "meshtastic_gps",
    "meshtastic_listen",
    "meshtastic_send_gate",
    "meshtastic_send",
}

KRY_COMMANDS = {
    "koala_kry",
    "koala_kry_run_replay",
    "koala_kry_transmit_review",
    "koala_kry_run_review",
    "koala_kry_prompt_status",
    "koala_kry_use_latest_capture",
    "koala_kry_speed_live",
    "koala_kry_speed_fast",
    "koala_kry_speed_instant",
    "koala_kry_limit_50",
    "koala_kry_limit_200",
    "koala_kry_limit_all",
    "koala_kry_rf_review_on",
    "koala_kry_rf_review_off",
    "koala_kry_lab_ack_on",
    "koala_kry_owned_ack_on",
    "koala_kry_clear_prompt",
}

KOALA_KAN_COMMANDS = {
    "koala_kan_kommander",
    "koala_kan_manifest",
    "koala_kan_inventory",
    "koala_kan_status",
    "koala_kan_listen_10s",
    "koala_kan_generate_payloads",
    "koala_kan_report",
    "koala_kan_transmit_gate",
    "koala_kan_listen_transmit_gate",
}

LAB_POLICY_COMMANDS = {
    "lab_transmit_policy_status",
    "lab_transmit_can_gated_bench",
    "lab_transmit_can_listen_only",
    "lab_transmit_can_disabled",
    "lab_transmit_bench_arm_on",
    "lab_transmit_bench_arm_off",
    "lab_transmit_rf_ble_gated_lab",
    "lab_transmit_rf_ble_listen_only",
    "lab_transmit_rf_ble_disabled",
    "lab_transmit_rf_ble_arm_on",
    "lab_transmit_rf_ble_arm_off",
    "lab_transmit_rf_ble_passive_only",
    "lab_transmit_rf_ble_disabled_install",
}

LAB_REPORT_COMMANDS = {
    "authorized_ble_inventory",
    "gatt_readiness_checklist",
    "pairing_security_review",
    "lab_beacon_plan",
    "packet_capture_notes",
    "defensive_lab_report",
    "defensive_report",
    "report",
}

SYSTEM_COMMANDS = {
    "killerkoala_voice",
    "buttons",
    "level/status",
    "wake killerkoala",
    "settings",
    "koala_mode_switcher",
    "shutdown_confirm",
    "power_toggle",
    "power_on_off",
    "reset_confirm",
    "reset",
    "reboot",
    "reset_reboot",
}

NEW_ACTION_COMMANDS = {
    "location_gate_gnss_current",
    "companion_status",
    "killerkoala_hybrid",
    "xp_status",
    "button_map",
    "firmware_version",
    "koala_kapture_transmit_placeholder",
    "koala_kry_transmit_placeholder",
    "koala_kan_transmit_placeholder",
}

MISC_COMMANDS = {
    "scan",
    "summary",
    "show",
    "location_gate_status",
    "koala_kapture",
    "boomerang",
    "twocan_vehicle_diagnostics",
    "twocan_clear_codes_safety_note",
    "vehicle_diagnostics_readiness",
    "vehicle_clear_codes_safety_note",
    "urban_poaching",
    "thats_not_a_knife",
    "anteater",
    "ear_tag",
    "ear_tag_tx_lab",
}

PLACEHOLDER_STATUSES = {
    "AUTOMATED_PLACEHOLDER_COMPLETE",
    "SYSTEM_ACTION_RECORDED",
    "PROMPT_ACTION_RECORDED",
    "BLUEZ_LAB_SCOPE_ACTION_RECORDED",
    "T114_ACTION_RECORDED",
    "MESHTASTIC_ACTION_RECORDED",
    "PROTECTED_BLUEZ_ACTION_RECORDED",
    "BLUEZ_WRAPPER_ACTION_RECORDED",
    "KOALA_KRY_ACTION_RECORDED",
    "KOALA_KAN_ACTION_RECORDED",
    "TWOCAN_ACTION_RECORDED",
}


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def _safe_read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _systemd_status(service: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        state = (proc.stdout or proc.stderr or "unknown").strip()
        return {"service": service, "state": state, "active": proc.returncode == 0}
    except Exception as exc:
        return {"service": service, "state": "unavailable", "active": False, "error": str(exc)}


def _ollama_status() -> dict[str, Any]:
    from .killerkoala_hybrid_companion import load_config

    config = load_config()
    payload: dict[str, Any] = {
        "host": config.host,
        "model": config.model,
        "mode": config.mode,
        "reachable": False,
        "model_installed": False,
        "models": [],
    }
    try:
        import httpx

        response = httpx.get(f"{config.host}/api/tags", timeout=1.5)
        response.raise_for_status()
        body = response.json()
        rows = body.get("models", []) if isinstance(body, dict) else []
        names = [str(row.get("name", "")) for row in rows if isinstance(row, dict) and row.get("name")]
        payload["reachable"] = True
        payload["models"] = names
        payload["model_installed"] = config.model in names or any(name.split(":", 1)[0] == config.model.split(":", 1)[0] for name in names)
    except Exception as exc:
        payload["error"] = str(exc)
    return payload


def _companion_status() -> dict[str, Any]:
    from .killerkoala_voice_control import load_xp_state, module_manifest

    voice = module_manifest()
    xp = asdict(load_xp_state())
    ollama = _ollama_status()
    service = _systemd_status("ollama.service")
    return {
        "status": "COMPANION_READY" if ollama.get("reachable") else "COMPANION_READY_WITH_PHRASE_FALLBACK",
        "wake_word": voice.get("wake_word", "killerkoala"),
        "voice_module_count": len(voice.get("modules", {})),
        "menu_action_count": int(voice.get("menu_action_count", 0)),
        "xp": xp,
        "local_ai": ollama,
        "ollama_service": service,
        "phrase_fallback_ready": True,
        "execution_owner": "raspberry-pi",
    }


def _hybrid_status() -> dict[str, Any]:
    payload = _companion_status()
    ollama = payload.get("local_ai", {})
    payload.update(
        {
            "status": "KILLERKOALA_HYBRID_READY" if isinstance(ollama, dict) and ollama.get("reachable") else "KILLERKOALA_HYBRID_FALLBACK_READY",
            "mode": "local_tinyllama_plus_phrase_fallback",
            "interactive_entrypoint": "scripts/run_killerkoala_hybrid.py",
            "blocking_session_started": False,
            "note": "The menu performs a non-blocking readiness check; voice requests use the installed hybrid companion runtime.",
        }
    )
    return payload


def _xp_status() -> dict[str, Any]:
    from .killerkoala_voice_control import DEFAULT_XP_PATH, load_xp_state

    state = asdict(load_xp_state())
    return {
        "status": "XP_STATUS_READY",
        "state": state,
        "state_path": str(DEFAULT_XP_PATH),
    }


def _button_map() -> dict[str, Any]:
    from .gpio_buttons import DEFAULT_BUTTONS, DEFAULT_ELECTRICAL_MODE

    rows = []
    for key, value in sorted(DEFAULT_BUTTONS.items(), key=lambda item: int(item[1].get("number", 0))):
        rows.append({"config_key": key, **value})
    control = _safe_read_json(Path("logs/control_mode.json"))
    return {
        "status": "BUTTON_MAP_READY",
        "buttons": rows,
        "electrical": asdict(DEFAULT_ELECTRICAL_MODE),
        "control_mode": control,
        "protected_holds": {"K7": 2.5, "K8": 3.0},
    }


def _firmware_version() -> dict[str, Any]:
    from . import __version__

    manifest_path = REPO_ROOT / "releases" / "koalabyte-blue-current" / "manifest.json"
    deployment_path = REPO_ROOT / "logs" / "deployment" / "whole_system_deployment_status.json"
    manifest = _safe_read_json(manifest_path)
    deployment = _safe_read_json(deployment_path)
    return {
        "status": "FIRMWARE_VERSION_READY",
        "package_version": __version__,
        "release_manifest_path": str(manifest_path),
        "release_manifest_present": manifest_path.exists(),
        "release_manifest": manifest,
        "deployment_status_path": str(deployment_path),
        "deployment_status": deployment,
    }


def _protected_gnss_current() -> dict[str, Any]:
    from . import menu_prompt_state
    from .gnss_location import current_fix, fix_to_dict
    from .location_password_gate import PASSWORD_FILE, UNLOCK_ENV, password_exists

    applied = menu_prompt_state.apply_location_gate_env()
    fix = current_fix(authorized=None, prompt=False)
    unlocked = os.environ.get(UNLOCK_ENV) in {"1", "true", "TRUE", "yes", "YES"}
    return {
        "status": "GNSS_FIX_READY" if fix is not None else "GNSS_FIX_LOCKED_OR_UNAVAILABLE",
        "fix": fix_to_dict(fix),
        "password_configured": password_exists(),
        "unlocked": unlocked,
        "password_path": str(PASSWORD_FILE),
        "menu_prompt_state": applied,
        "source_priority": "environment, saved T114 fix, live T114 serial, then configured Meshtastic",
    }


def _rf_ble_safety_check(command: str, subsystem: str) -> dict[str, Any]:
    from . import lab_transmit_policy

    gate = lab_transmit_policy.rf_ble_transmit_gate_status()
    payload = {
        "status": "RF_BLE_TRANSMIT_SAFETY_CHECK_COMPLETE",
        "command": command,
        "subsystem": subsystem,
        "gate": gate,
        "gate_would_allow_synthetic_beacon": bool(gate.get("allowed")),
        "radio_action_performed": False,
        "payloads_requested": [],
        "payloads_sent": [],
        "allowed_when_armed": "bounded non-connectable fixed-name synthetic lab beacon",
        "always_blocked": [
            "captured signal replay",
            "captured identifier rebroadcast",
            "pairing or connection attempts",
            "GATT writes",
            "impersonation, disruption, or jamming",
        ],
        "updated_at": time.time(),
    }
    path = OUTPUT_DIR / f"{command}_safety_check.json"
    payload["artifact_path"] = _write_json(path, payload)
    return payload


def _can_safety_check(command: str) -> dict[str, Any]:
    from . import lab_transmit_policy

    gate = lab_transmit_policy.can_transmit_gate_status()
    payload = {
        "status": "CAN_TRANSMIT_SAFETY_CHECK_COMPLETE",
        "command": command,
        "gate": gate,
        "gate_would_allow_synthetic_bench_frames": bool(gate.get("allowed")),
        "can_action_performed": False,
        "frames_requested": [],
        "frames_sent": [],
        "allowed_when_armed": "synthetic heartbeat payloads on an isolated owned bench simulator",
        "always_blocked": [
            "vehicle or industrial-controller writes",
            "UDS security access or ECU coding",
            "DTC clearing or actuator commands",
            "captured traffic replay",
        ],
        "updated_at": time.time(),
    }
    path = OUTPUT_DIR / f"{command}_safety_check.json"
    payload["artifact_path"] = _write_json(path, payload)
    return payload


def _keyboard_route(command: str) -> dict[str, Any]:
    field = command.split(":", 1)[1] if ":" in command else ""
    return {
        "status": "KEYBOARD_UI_ROUTE_READY",
        "command": command,
        "field": field,
        "ui_action": "open_protected_keyboard" if "password" in field or "token" in field or "key" in field else "open_keyboard",
        "note": "The wrapped menu opens the keyboard directly; this result keeps voice/direct dispatch from falling through to a placeholder.",
    }


def _new_action_handlers() -> dict[str, Callable[[], dict[str, Any]]]:
    return {
        "location_gate_gnss_current": _protected_gnss_current,
        "companion_status": _companion_status,
        "killerkoala_hybrid": _hybrid_status,
        "xp_status": _xp_status,
        "button_map": _button_map,
        "firmware_version": _firmware_version,
        "koala_kapture_transmit_placeholder": lambda: _rf_ble_safety_check("koala_kapture_transmit_placeholder", "Koala Kapture"),
        "koala_kry_transmit_placeholder": lambda: _rf_ble_safety_check("koala_kry_transmit_placeholder", "Koala Kry"),
        "koala_kan_transmit_placeholder": lambda: _can_safety_check("koala_kan_transmit_placeholder"),
    }


def _plugin_capability(command: str) -> dict[str, Any] | None:
    try:
        from . import greatwhite_reef

        if greatwhite_reef._is_greatwhite_command(command):
            return {"concrete": True, "category": "greatwhite_reef", "backend": "greatwhite_reef.run_greatwhite_menu_action"}
    except Exception:
        if command.startswith("greatwhite_pcap_read:") or command.startswith("greatwhite_") or command.startswith("great_wire_shark_"):
            return {"concrete": True, "category": "greatwhite_reef", "backend": "greatwhite_reef"}

    try:
        from . import twocan_read_only

        if command in twocan_read_only.TWOCAN_COMMANDS:
            return {"concrete": True, "category": "twocan_read_only", "backend": "twocan_read_only.run_twocan_menu_action"}
    except Exception:
        pass

    try:
        from . import mopidy_player

        if mopidy_player._is_music_command(command):
            return {"concrete": True, "category": "lyrebird", "backend": "mopidy_player.run_music_command"}
    except Exception:
        if command.startswith("music_song:") or command.startswith("music_preset:") or command.startswith("music_"):
            return {"concrete": True, "category": "lyrebird", "backend": "mopidy_player"}

    try:
        from . import rf_ble_lab_gates

        if command in rf_ble_lab_gates.ACTIVE_GATE_COMMANDS:
            return {"concrete": True, "category": "rf_ble_lab_gate", "backend": "rf_ble_lab_gates.run_gate_command"}
    except Exception:
        pass
    return None


def classify_command(command: str) -> dict[str, Any]:
    command = str(command or "").strip()
    if not command:
        return {"concrete": False, "category": "invalid", "backend": "none"}
    if command.startswith("submenu:"):
        return {"concrete": True, "category": "ui_submenu", "backend": "menu_ui.open_submenu"}
    if command.startswith("status:"):
        return {"concrete": True, "category": "ui_status", "backend": "t114_menu_status"}
    if command.startswith("keyboard:"):
        return {"concrete": True, "category": "ui_keyboard", "backend": "menu keyboard mode"}
    if command == "quit":
        return {"concrete": True, "category": "ui_quit", "backend": "menu process"}
    if command in NEW_ACTION_COMMANDS:
        return {"concrete": True, "category": "menu_actionability", "backend": "menu_actionability handler"}
    plugin = _plugin_capability(command)
    if plugin is not None:
        return plugin
    if command in LAB_POLICY_COMMANDS:
        return {"concrete": True, "category": "lab_policy", "backend": "lab_transmit_policy.run_menu_action"}
    if command in PROMPT_COMMANDS:
        return {"concrete": True, "category": "prompt_state", "backend": "menu_prompt_state"}
    if command in BLUEZ_SCOPE_COMMANDS:
        return {"concrete": True, "category": "bluez_scope", "backend": "bluez_lab_scope"}
    if command in EUCALYPTUS_COMMANDS:
        return {"concrete": True, "category": "eucalyptus", "backend": "eucalyptus_wigle/control"}
    if command in KRUISIN_COMMANDS:
        return {"concrete": True, "category": "kruisin", "backend": "koala_kombat_kruisin.control"}
    if command in BLUEZ_WRAPPER_COMMANDS:
        return {"concrete": True, "category": "bluez", "backend": "bluez_tools"}
    if command in PROTECTED_BLUEZ_COMMANDS:
        return {"concrete": True, "category": "protected_bluez", "backend": "bluez_protected_lab"}
    if command in T114_COMMANDS:
        return {"concrete": True, "category": "t114", "backend": "t114_bluez/gnss_location"}
    if command in MESHTASTIC_COMMANDS:
        return {"concrete": True, "category": "meshtastic", "backend": "meshtastic_app"}
    if command in KRY_COMMANDS:
        return {"concrete": True, "category": "koala_kry", "backend": "koala_kry"}
    if command in KOALA_KAN_COMMANDS:
        return {"concrete": True, "category": "koala_kan", "backend": "koala_kan_kommander"}
    if command in LAB_REPORT_COMMANDS:
        return {"concrete": True, "category": "lab_report", "backend": "authorized_lab_actions"}
    if command in SYSTEM_COMMANDS:
        return {"concrete": True, "category": "system", "backend": "menu_action_runner._system_status"}
    if command in MISC_COMMANDS:
        return {"concrete": True, "category": "misc", "backend": "menu_action_runner concrete helper"}
    return {"concrete": False, "category": "unsupported", "backend": "none"}


def _placeholder_paths(value: Any, prefix: str = "result") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        status = str(value.get("status", ""))
        if status in PLACEHOLDER_STATUSES or status.endswith("_ACTION_RECORDED"):
            paths.append(f"{prefix}.status={status}")
        for key, item in value.items():
            paths.extend(_placeholder_paths(item, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_placeholder_paths(item, f"{prefix}[{index}]"))
    return paths


def _normalize_menu_descriptions() -> None:
    from . import menu_catalog

    replacements = {
        "koala_kapture_transmit_placeholder": "Inspect the RF/BLE gate and write a safety artifact without transmitting.",
        "koala_kry_transmit_placeholder": "Inspect the RF/BLE gate and write a safety artifact without transmitting.",
        "koala_kan_transmit_placeholder": "Inspect the CAN bench gate and write a safety artifact without sending frames.",
        "killerkoala_hybrid": "Check local TinyLlama, Ollama service, and phrase-fallback readiness.",
    }
    for row in menu_catalog.all_menu_entries():
        command = str(row.get("command", ""))
        if command in replacements:
            row["description"] = replacements[command]


def build_actionability_manifest() -> tuple[dict[str, Any], list[str]]:
    from . import menu_catalog

    _normalize_menu_descriptions()
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    menus: dict[str, list[dict[str, object]]] = {"main": list(menu_catalog.MAIN_MENU_ITEMS)}
    for menu_name in list(menu_catalog.SUBMENU_ITEMS.keys()):
        menus[menu_name] = list(menu_catalog._entries_for_menu(menu_name))

    enabled_leaf_count = 0
    for menu_name, entries in menus.items():
        for entry in entries:
            command = str(entry.get("command", "")).strip()
            enabled = bool(entry.get("enabled", True))
            capability = classify_command(command)
            is_leaf = not command.startswith("submenu:")
            if enabled and is_leaf:
                enabled_leaf_count += 1
                if not capability.get("concrete"):
                    failures.append(f"{menu_name}: {entry.get('label')} has no concrete action: {command}")
            description = str(entry.get("description", ""))
            label = str(entry.get("label", ""))
            if enabled and ("placeholder" in label.lower() or "placeholder" in description.lower() or "intentionally non-operational" in description.lower()):
                failures.append(f"{menu_name}: placeholder wording remains visible for {label}: {command}")
            rows.append(
                {
                    "menu": menu_name,
                    "label": label,
                    "command": command,
                    "enabled": enabled,
                    "is_leaf": is_leaf,
                    **capability,
                }
            )

    payload = {
        "status": "MENU_ACTIONABILITY_READY" if not failures else "MENU_ACTIONABILITY_INCOMPLETE",
        "updated_at": time.time(),
        "menu_count": len(menus),
        "entry_count": len(rows),
        "enabled_leaf_count": enabled_leaf_count,
        "concrete_enabled_leaf_count": sum(1 for row in rows if row["enabled"] and row["is_leaf"] and row["concrete"]),
        "unsupported_enabled_leaf_count": len(failures),
        "legacy_safety_command_ids": {
            "koala_kapture_transmit_placeholder": "concrete RF/BLE safety check",
            "koala_kry_transmit_placeholder": "concrete RF/BLE safety check",
            "koala_kan_transmit_placeholder": "concrete CAN safety check",
        },
        "generic_placeholder_results_fail_closed": True,
        "rows": rows,
        "failures": failures,
    }
    _write_json(MANIFEST_PATH, payload)
    _write_json(
        STATUS_PATH,
        {
            "status": payload["status"],
            "manifest_path": str(MANIFEST_PATH),
            "failures": failures,
            "updated_at": payload["updated_at"],
        },
    )
    return payload, failures


def install_menu_actionability() -> None:
    from . import menu_action_runner

    if getattr(menu_action_runner, "_koalabyte_menu_actionability_installed", False):
        return

    _normalize_menu_descriptions()
    original = menu_action_runner.run_automated_menu_action
    handlers = _new_action_handlers()

    def routed(command: str, label: str = "", group: str = "") -> dict[str, Any]:
        command = str(command or "").strip()
        try:
            if command.startswith("keyboard:"):
                return menu_action_runner._ok(command, label, _keyboard_route(command), "AUTOMATED_UI_ACTION_COMPLETE")
            handler = handlers.get(command)
            if handler is not None:
                return menu_action_runner._ok(command, label, handler())
            capability = classify_command(command)
            if not capability.get("concrete"):
                raise RuntimeError(f"No concrete menu implementation is registered for {command!r}")
            result = original(command, label, group)
            placeholder_paths = _placeholder_paths(result)
            if placeholder_paths:
                raise RuntimeError(
                    f"Menu command {command!r} reached placeholder result paths: {', '.join(placeholder_paths)}"
                )
            if isinstance(result, dict):
                result.setdefault("menu_actionability", capability)
            return result
        except Exception as exc:
            return menu_action_runner._error(command, label, exc)

    routed.__name__ = "run_automated_menu_action_without_placeholders"
    routed.__doc__ = "Dispatch every visible menu leaf to a concrete action and fail closed on placeholder results."
    menu_action_runner.run_automated_menu_action = routed
    menu_action_runner._koalabyte_menu_actionability_installed = True
