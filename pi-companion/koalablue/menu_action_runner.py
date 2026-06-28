from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("logs/menu_actions")


def _write_json(name: str, payload: dict[str, Any]) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)[:72] or "action"
    path = OUTPUT_DIR / f"{safe}_{int(time.time())}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def _ok(command: str, label: str, result: Any, status: str = "AUTOMATED_ACTION_COMPLETE") -> dict[str, Any]:
    payload = {"status": status, "command": command, "label": label, "result": result, "timestamp": time.time()}
    payload["artifact_path"] = _write_json(command, payload)
    return payload


def _error(command: str, label: str, exc: Exception) -> dict[str, Any]:
    payload = {"status": "AUTOMATED_ACTION_SKIPPED", "command": command, "label": label, "error": str(exc), "timestamp": time.time()}
    payload["artifact_path"] = _write_json(command, payload)
    return payload


def _lab_action(command: str) -> dict[str, Any]:
    from .authorized_lab_actions import AuthorizedLabActions

    result = AuthorizedLabActions().run(command, authorized=True, context={"source": "menu_select"})
    return asdict(result)


def _status_row(command: str) -> dict[str, Any]:
    from .t114_menu_status import status_label_description

    label, description = status_label_description(command)
    return {"status": "STATUS_ROW_CHECKED", "status_label": label, "description": description}


def _ble_scan_summary(command: str) -> dict[str, Any]:
    from .bluez_tools import scan, status

    if command == "scan":
        return asdict(scan(duration_seconds=10))
    if command == "summary":
        return {"status": asdict(status()), "summary": "Local Bluetooth status collected."}
    return asdict(status())


def _koala_kapture() -> dict[str, Any]:
    from .koala_kapture import KoalaKaptureConfig, KoalaKaptureRecorder

    cfg = KoalaKaptureConfig(duration_seconds=12.0, scan_window_seconds=4.0, max_records=300)
    return asdict(asyncio.run(KoalaKaptureRecorder(cfg).record()))


def _koala_kry(review_only: bool = False) -> dict[str, Any]:
    from .koala_kry import KoalaKryConfig, KoalaKryReplay

    cfg = KoalaKryConfig(max_records=200, speed=0, write_transmit_review=review_only, request_rf_transmit=False)
    return asdict(KoalaKryReplay(cfg).replay())


def _urban_poaching() -> dict[str, Any]:
    from .urban_poaching import UrbanPoachingConfig, UrbanPoachingGame

    cfg = UrbanPoachingConfig(rounds=3, scan_seconds=3.0)
    return asdict(asyncio.run(UrbanPoachingGame(cfg).play()))


def _koala_kan() -> dict[str, Any]:
    from .koala_kan_kommander import inventory, manifest, status

    return {"manifest": manifest(), "inventory": inventory(), "status": status()}


def _defense_guard() -> dict[str, Any]:
    from .ble_defense_guard import load_monitor_settings

    return {"status": "DEFENSE_GUARD_SETTINGS_READY", "settings": load_monitor_settings()}


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
        return {"status": "VOICE_PREVIEW_READY", "wake_word": "killerkoala", "mode": "menu_preview"}
    if command == "koala_mode_switcher":
        return {"status": "MODE_SWITCHER_STATUS_READY", "note": "Legacy dongle mode package helper is selectable without extra prompt."}
    if command == "shutdown_confirm":
        return {"status": "SHUTDOWN_CONFIRM_RECORDED", "note": "Shutdown request logged. Use the OS power command when ready."}
    return {"status": "SYSTEM_ACTION_RECORDED"}


def run_automated_menu_action(command: str, label: str = "", group: str = "") -> dict[str, Any]:
    try:
        if command.startswith("status:"):
            return _ok(command, label, _status_row(command), "AUTOMATED_STATUS_COMPLETE")
        if command in {"scan", "summary", "show"}:
            return _ok(command, label, _ble_scan_summary(command))
        if command == "koala_kapture":
            return _ok(command, label, _koala_kapture())
        if command == "koala_kry":
            return _ok(command, label, _koala_kry(False))
        if command == "koala_kry_transmit_review":
            return _ok(command, label, _koala_kry(True))
        if command in {"authorized_ble_inventory", "gatt_readiness_checklist", "pairing_security_review", "lab_beacon_plan", "packet_capture_notes", "defensive_report", "report"}:
            return _ok(command, label, _lab_action("defensive_report" if command == "report" else command))
        if command == "koala_kan_kommander":
            return _ok(command, label, _koala_kan())
        if command == "urban_poaching":
            return _ok(command, label, _urban_poaching())
        if command == "thats_not_a_knife":
            return _ok(command, label, _defense_guard())
        if command in {"ear_tag", "ear_tag_tx_lab"}:
            return _ok(command, label, {"status": "LAB_BEACON_PLAN_READY", "result": _lab_action("lab_beacon_plan")})
        if command in {"killerkoala_voice", "buttons", "level/status", "wake killerkoala", "settings", "koala_mode_switcher", "shutdown_confirm"}:
            return _ok(command, label, _system_status(command))
        return _ok(command, label, {"status": "AUTOMATED_PLACEHOLDER_COMPLETE", "command": command, "group": group})
    except Exception as exc:
        return _error(command, label, exc)
