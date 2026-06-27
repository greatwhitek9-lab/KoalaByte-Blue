from __future__ import annotations

import os
import time
from dataclasses import asdict
from pathlib import Path

from .bluez_tools import BluezRunResult, CommandResult, DEFAULT_OUTPUT_DIR, _base_safety, _run, _write_json, gatt_readiness, info, module_manifest, redact_addresses, services
from .location_password_gate import UNLOCK_ENV, ensure_unlocked, password_exists

TARGET_ENV = "KOALABYTE_BLUEZ_LAB_TARGET"
ALT_TARGET_ENV = "KOALABYTE_BLUEZ_TARGET"
OWNED_ENV = "KOALABYTE_BLUEZ_OWNED_DEVICE"


def _output_dir(path: Path = DEFAULT_OUTPUT_DIR) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _target() -> str:
    return os.environ.get(TARGET_ENV, "").strip() or os.environ.get(ALT_TARGET_ENV, "").strip()


def _owned() -> bool:
    return os.environ.get(OWNED_ENV, "").strip() in {"1", "true", "TRUE", "yes", "YES", "owned", "OWNED"}


def _gate_unlocked() -> bool:
    return ensure_unlocked(prompt=os.isatty(0))


def _safety(*, owned_device: bool, target_required: bool) -> dict[str, object]:
    safety = _base_safety(raw_addresses=False, owned_device=owned_device)
    safety.update(
        {
            "protected_action_password_configured": password_exists(),
            "protected_action_unlocked": os.environ.get(UNLOCK_ENV) in {"1", "true", "TRUE", "yes", "YES"},
            "protected_action_required": True,
            "target_required": target_required,
            "owned_device_env": OWNED_ENV,
            "target_env": TARGET_ENV,
        }
    )
    return safety


def _blocked(action: str, title: str, reason: str, output_dir: Path, *, target_required: bool) -> BluezRunResult:
    started = time.time()
    target = _target()
    owned_device = _owned()
    result = CommandResult(command=[action], returncode=2, stdout="", stderr="", skipped=True, reason=reason)
    ended = time.time()
    out = output_dir / f"koala_bluez_{action}_{int(started)}.json"
    payload = BluezRunResult(
        action=action,
        theme_title=title,
        started_at=started,
        ended_at=ended,
        output_dir=str(output_dir),
        results=[result],
        artifacts={"blocked_summary": str(out)},
        safety=_safety(owned_device=owned_device, target_required=target_required),
    )
    record = asdict(payload)
    record["target"] = redact_addresses(target) if target else ""
    record["help"] = [
        "Set up a protected-actions password first: PYTHONPATH=pi-companion python3 scripts/run_location_password_gate.py setup",
        "Terminal menu mode will prompt for the password when a protected action is selected.",
        f"For target-specific owned-device checks set {TARGET_ENV}=AA:BB:CC:DD:EE:FF",
        f"For target-specific owned-device checks set {OWNED_ENV}=1",
    ]
    _write_json(out, record)
    return payload


def protected_bluez_manifest(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    return module_manifest(_output_dir(output_dir))


def protected_target_info(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    output_dir = _output_dir(output_dir)
    target = _target()
    if not _gate_unlocked():
        return _blocked("joey_target_dossier", "Joey Target Dossier", "protected actions password is locked", output_dir, target_required=True)
    if not target or not _owned():
        return _blocked("joey_target_dossier", "Joey Target Dossier", "owned-device target is required", output_dir, target_required=True)
    result = info(target, True, output_dir=output_dir, raw_addresses=False)
    result.theme_title = "Joey Target Dossier"
    return result


def protected_target_services(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    output_dir = _output_dir(output_dir)
    target = _target()
    if not _gate_unlocked():
        return _blocked("treehouse_service_trace", "Treehouse Service Trace", "protected actions password is locked", output_dir, target_required=True)
    if not target or not _owned():
        return _blocked("treehouse_service_trace", "Treehouse Service Trace", "owned-device target is required", output_dir, target_required=True)
    result = services(target, True, output_dir=output_dir, raw_addresses=False)
    result.theme_title = "Treehouse Service Trace"
    return result


def protected_gatt_readiness(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BluezRunResult:
    output_dir = _output_dir(output_dir)
    target = _target()
    if not _gate_unlocked():
        return _blocked("gumnut_gatt_gatecheck", "Gumnut GATT Gatecheck", "protected actions password is locked", output_dir, target_required=True)
    if not target or not _owned():
        return _blocked("gumnut_gatt_gatecheck", "Gumnut GATT Gatecheck", "owned-device target is required", output_dir, target_required=True)
    result = gatt_readiness(target, True, output_dir=output_dir)
    result.theme_title = "Gumnut GATT Gatecheck"
    return result


def _protected_command(action: str, title: str, command: list[str], output_name: str, *, target_required: bool = False) -> BluezRunResult:
    output_dir = _output_dir(DEFAULT_OUTPUT_DIR)
    target = _target()
    if not _gate_unlocked():
        return _blocked(action, title, "protected actions password is locked", output_dir, target_required=target_required)
    if target_required and (not target or not _owned()):
        return _blocked(action, title, "owned-device target is required", output_dir, target_required=True)

    started = time.time()
    result = _run(command, timeout_seconds=15, raw_addresses=False)
    if target:
        result.command = [redact_addresses(part) for part in result.command]
    ended = time.time()
    out = output_dir / f"{output_name}_{int(started)}.json"
    payload = BluezRunResult(
        action=action,
        theme_title=title,
        started_at=started,
        ended_at=ended,
        output_dir=str(output_dir),
        results=[result],
        artifacts={action: str(out)},
        safety=_safety(owned_device=_owned(), target_required=target_required),
    )
    _write_json(out, asdict(payload))
    return payload


def outback_radio_ledger() -> BluezRunResult:
    return _protected_command("outback_radio_ledger", "Outback Radio Ledger", ["hciconfig", "-a"], "koala_bluez_outback_radio_ledger")


def classic_track_finder() -> BluezRunResult:
    return _protected_command("classic_track_finder", "Classic Track Finder", ["hcitool", "dev"], "koala_bluez_classic_track_finder")


def treehouse_rfcomm_wiremap() -> BluezRunResult:
    return _protected_command("treehouse_rfcomm_wiremap", "Treehouse RFCOMM Wiremap", ["rfcomm", "-a"], "koala_bluez_treehouse_rfcomm_wiremap")


def pouch_link_echo() -> BluezRunResult:
    target = _target()
    command = ["l2ping", "-c", "1", target or "00:00:00:00:00:00"]
    return _protected_command("pouch_link_echo", "Pouch Link Echo", command, "koala_bluez_pouch_link_echo", target_required=True)


def gumnut_gatt_ghostmap() -> BluezRunResult:
    target = _target()
    command = ["gatttool", "-b", target or "00:00:00:00:00:00", "--primary"]
    return _protected_command("gumnut_gatt_ghostmap", "Gumnut GATT Ghostmap", command, "koala_bluez_gumnut_gatt_ghostmap", target_required=True)


def platypus_bt_proxy() -> BluezRunResult:
    return _protected_command("platypus_bt_proxy", "Platypus BT-Proxy", ["btproxy", "--help"], "koala_bluez_platypus_bt_proxy")
