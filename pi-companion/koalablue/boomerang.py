#!/usr/bin/env python3
"""Boomerang camera-awareness action.

Boomerang is an interactive manual/public observation logbook. It stays open
until the operator quits and records only lawful, non-network camera-awareness
identity details.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .camera_awareness_logger import (
    LOG_ROOT,
    append_observation,
    build_summary,
    create_observation,
    export_csv,
    export_json,
    load_observations,
)
from .menu_theme import render_terminal_eucalyptus_card

ACTION_NAME = "Boomerang"
DESCRIPTION = (
    "Boomerang is a manual camera-awareness logbook. It records public/visible "
    "camera details, assigns local IDs, awards killerkoala XP, exports reports, "
    "and stays open until quit."
)
SCOPE = "manual/public observation only; no RF scanning, network probing, MAC/IP IDs, or avoidance routing"
XP_REWARD_PER_LOG = 10
DEFAULT_XP_PATH = Path("logs/killerkoala/xp_state.json")
DEFAULT_ALERT_LOG = Path("logs/killerkoala/boomerang_alerts.jsonl")

KILLERKOALA_BOOMERANG_ALERTS = {
    "boomerang_start": "BOOMerang!",
    "camera_found": "Crikey, mate — Camera found and logged. Boomerang tagged that cheeky lens clean.",
    "xp_gain": "killerkoala gained XP. Another notch in the gumtree.",
}


def _rank_for_xp(xp: int) -> str:
    if xp >= 250:
        return "Legend"
    if xp >= 75:
        return "Hacker"
    return "Noob"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _load_xp(path: Path = DEFAULT_XP_PATH) -> dict:
    if not path.exists():
        return {"xp": 0, "rank": _rank_for_xp(0), "successful_modules": 0, "failed_modules": 0, "last_module": "", "updated_at": time.time()}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        xp = int(data.get("xp", 0))
        return {
            "xp": xp,
            "rank": _rank_for_xp(xp),
            "successful_modules": int(data.get("successful_modules", 0)),
            "failed_modules": int(data.get("failed_modules", 0)),
            "last_module": str(data.get("last_module", "")),
            "updated_at": float(data.get("updated_at", time.time())),
            "boomerang_logs": int(data.get("boomerang_logs", 0)),
        }
    except Exception:
        return {"xp": 0, "rank": _rank_for_xp(0), "successful_modules": 0, "failed_modules": 0, "last_module": "", "updated_at": time.time(), "boomerang_logs": 0}


def _resolve_tts_command(preferred: Optional[str] = None) -> Optional[str]:
    candidates = [preferred] if preferred else []
    candidates.extend(["espeak-ng", "espeak", "say"])
    for candidate in candidates:
        if candidate and shutil.which(candidate):
            return candidate
    return None


def speak_killerkoala_alert(
    event: str,
    *,
    context: Optional[dict] = None,
    tts_enabled: Optional[bool] = None,
    alert_log: str | Path = DEFAULT_ALERT_LOG,
    tts_command: Optional[str] = None,
) -> str:
    """Emit a separate KillerKoala alert for a Boomerang event.

    Audio is optional and controlled by KOALABYTE_TTS=1 or tts_enabled=True.
    The alert always prints and logs, even when a TTS engine is unavailable.
    """

    line = KILLERKOALA_BOOMERANG_ALERTS.get(event, f"killerkoala alert: {event}")
    context = dict(context or {})
    reward = context.get("xp_reward")
    xp_after = context.get("xp_after")
    rank = context.get("rank")
    camera_label = context.get("camera_label")
    local_asset_id = context.get("local_asset_id")

    if event == "camera_found" and camera_label:
        line = f"{line} {camera_label} is stored as {local_asset_id or 'a local asset'}."
    if event == "xp_gain" and reward is not None:
        line = f"{line} Plus {reward} XP. Total {xp_after}. Rank {rank}."

    payload = {
        "action": ACTION_NAME,
        "event": event,
        "line": line,
        "context": context,
        "timestamp": time.time(),
        "verbal_alert": True,
    }
    _append_jsonl(Path(alert_log), payload)
    print(f"killerkoala alert [{event}]: {line}")

    enabled = tts_enabled if tts_enabled is not None else os.environ.get("KOALABYTE_TTS", "0") == "1"
    command = _resolve_tts_command(tts_command) if enabled else None
    if command:
        try:
            subprocess.run([command, line], check=False, timeout=6)
        except Exception:
            pass
    return line


def award_boomerang_xp(reward: int = XP_REWARD_PER_LOG, xp_path: str | Path = DEFAULT_XP_PATH) -> tuple[int, int, str]:
    path = Path(xp_path)
    state = _load_xp(path)
    before = int(state.get("xp", 0))
    after = before + int(reward)
    state["xp"] = after
    state["rank"] = _rank_for_xp(after)
    state["successful_modules"] = int(state.get("successful_modules", 0)) + 1
    state["boomerang_logs"] = int(state.get("boomerang_logs", 0)) + 1
    state["last_module"] = ACTION_NAME
    state["updated_at"] = time.time()
    _write_json(path, state)
    return before, after, str(state["rank"])


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value if value else default


def _prompt_float(label: str) -> Optional[float]:
    value = input(f"{label} (blank to skip): ").strip()
    if not value:
        return None
    return float(value)


def _show_home(log_root: Path) -> None:
    observations = load_observations(log_root)
    summary = build_summary(observations)
    xp = _load_xp(DEFAULT_XP_PATH)
    rows = [
        DESCRIPTION,
        f"Scope: {SCOPE}",
        f"Stored observations: {summary['count']}",
        f"XP reward: +{XP_REWARD_PER_LOG} per successfully logged camera record",
        f"killerkoala XP: {xp.get('xp', 0)} | Rank: {xp.get('rank', 'Noob')}",
        "Verbal alerts: start | camera found/logged | XP gained",
        "Commands: add | list | export | help | quit",
    ]
    print(render_terminal_eucalyptus_card("Boomerang", rows, subtitle="camera awareness action"))


def _show_help() -> None:
    rows = [
        "Boomerang comes back with the details you recorded: local ID, visible markings, public source, location, mounting notes, and confidence.",
        f"killerkoala earns +{XP_REWARD_PER_LOG} XP for every camera record successfully logged through this action.",
        "Separate killerkoala alerts fire when Boomerang starts, when a camera record is saved, and when XP is gained.",
        "Use add to enter one manually observed/public camera record.",
        "Use list to review stored records.",
        "Use export to write JSON and CSV reports.",
        "Use quit or q to return to the KoalaByte menu.",
        "Do not enter MAC, BSSID, SSID, IP, Bluetooth, RF fingerprint, probe, scan, or evasion data.",
    ]
    print(render_terminal_eucalyptus_card("What Boomerang Does", rows, subtitle="boomerang"))


def _add_observation(log_root: Path) -> None:
    print(render_terminal_eucalyptus_card("Add Camera Observation", [SCOPE], subtitle="boomerang"))
    label = _prompt("Label", "Unnamed public camera")
    camera_type = _prompt("Type", "unknown camera")
    location_text = _prompt("Location text")
    latitude = _prompt_float("Latitude")
    longitude = _prompt_float("Longitude")
    confidence = _prompt("Confidence unknown/low/medium/high", "unknown").lower()
    public_agency = _prompt("Public agency/source name")
    public_source_url = _prompt("Public source URL")
    visible_markings = _prompt("Visible markings")
    pole_or_mount_id = _prompt("Pole or mount ID visible from public view")
    public_asset_tag = _prompt("Public asset/permit tag")
    visible_make_model = _prompt("Visible make/model", "unknown")
    mounting_description = _prompt("Mounting description")
    facing_direction = _prompt("Facing direction")
    photo_reference = _prompt("Local photo reference")
    notes = _prompt("Notes", "Manual public observation only; no RF or network probing performed.")

    observation = create_observation(
        label=label,
        camera_type=camera_type,
        location_text=location_text,
        latitude=latitude,
        longitude=longitude,
        confidence=confidence,
        public_agency=public_agency,
        public_source_url=public_source_url,
        visible_markings=visible_markings,
        pole_or_mount_id=pole_or_mount_id,
        public_asset_tag=public_asset_tag,
        visible_make_model=visible_make_model,
        mounting_description=mounting_description,
        facing_direction=facing_direction,
        photo_reference=photo_reference,
        notes=notes,
    )
    path = append_observation(observation, log_root)
    speak_killerkoala_alert(
        "camera_found",
        context={
            "camera_label": observation.label,
            "local_asset_id": observation.local_asset_id,
            "observation_id": observation.observation_id,
        },
    )
    xp_before, xp_after, rank = award_boomerang_xp()
    speak_killerkoala_alert(
        "xp_gain",
        context={
            "xp_reward": XP_REWARD_PER_LOG,
            "xp_before": xp_before,
            "xp_after": xp_after,
            "rank": rank,
            "camera_label": observation.label,
            "local_asset_id": observation.local_asset_id,
        },
    )
    rows = [
        f"Saved to: {path}",
        f"Local asset ID: {observation.local_asset_id}",
        f"Observation ID: {observation.observation_id}",
        f"Label: {observation.label}",
        f"killerkoala XP: {xp_before} -> {xp_after} (+{XP_REWARD_PER_LOG})",
        f"Rank: {rank}",
    ]
    print(render_terminal_eucalyptus_card("Saved + XP Awarded", rows, subtitle="boomerang"))


def _list_observations(log_root: Path) -> None:
    observations = load_observations(log_root)
    if not observations:
        print(render_terminal_eucalyptus_card("No Observations Yet", ["Use add to record a manual/public observation."], subtitle="boomerang"))
        return
    rows = []
    for observation in observations[-12:]:
        rows.append(
            f"{observation.local_asset_id} | {observation.label} | {observation.camera_type} | {observation.location_text} | {observation.confidence}"
        )
    print(render_terminal_eucalyptus_card("Recent Boomerang Observations", rows, subtitle="boomerang"))


def _export_observations(log_root: Path) -> None:
    observations = load_observations(log_root)
    json_path = export_json(observations, log_root)
    csv_path = export_csv(observations, log_root)
    rows = [
        f"JSON: {json_path}",
        f"CSV: {csv_path}",
        f"Records exported: {len(observations)}",
    ]
    print(render_terminal_eucalyptus_card("Export Complete", rows, subtitle="boomerang"))


def run_interactive(log_root: str | Path = LOG_ROOT) -> int:
    root = Path(log_root)
    speak_killerkoala_alert("boomerang_start", context={"log_root": str(root)})
    _show_home(root)
    while True:
        command = input("boomerang> ").strip().lower()
        if command in {"q", "quit", "exit", "back", "menu"}:
            print(render_terminal_eucalyptus_card("Boomerang Closed", ["Returning to KoalaByte Blue menu."], subtitle="boomerang"))
            return 0
        if command in {"", "help", "h", "?"}:
            _show_help()
            continue
        if command == "add":
            try:
                _add_observation(root)
            except ValueError as exc:
                print(render_terminal_eucalyptus_card("Input Refused", [str(exc)], subtitle="boomerang"))
            continue
        if command == "list":
            _list_observations(root)
            continue
        if command == "export":
            _export_observations(root)
            continue
        if command == "json":
            print(json.dumps([asdict(o) for o in load_observations(root)], indent=2, sort_keys=True))
            continue
        print(render_terminal_eucalyptus_card("Unknown Command", ["Use add, list, export, help, or quit."], subtitle="boomerang"))


def run_cli(argv: Optional[list[str]] = None) -> int:
    return run_interactive()
