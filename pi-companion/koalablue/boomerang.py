#!/usr/bin/env python3
"""Boomerang camera-awareness action.

Boomerang is an interactive manual/public observation logbook. It stays open
until the operator quits and records only lawful, non-network camera-awareness
identity details.
"""

from __future__ import annotations

import json
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
    "camera details, assigns local IDs, exports reports, and stays open until quit."
)
SCOPE = "manual/public observation only; no RF scanning, network probing, MAC/IP IDs, or avoidance routing"


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
    rows = [
        DESCRIPTION,
        f"Scope: {SCOPE}",
        f"Stored observations: {summary['count']}",
        "Commands: add | list | export | help | quit",
    ]
    print(render_terminal_eucalyptus_card("Boomerang", rows, subtitle="camera awareness action"))


def _show_help() -> None:
    rows = [
        "Boomerang comes back with the details you recorded: local ID, visible markings, public source, location, mounting notes, and confidence.",
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
    rows = [
        f"Saved to: {path}",
        f"Local asset ID: {observation.local_asset_id}",
        f"Observation ID: {observation.observation_id}",
        f"Label: {observation.label}",
    ]
    print(render_terminal_eucalyptus_card("Saved", rows, subtitle="boomerang"))


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
