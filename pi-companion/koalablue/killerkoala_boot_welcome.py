#!/usr/bin/env python3
"""KillerKoala mode-aware boot welcome alerts.

The welcome alert runs after the pre-boot mode selector and before the normal
menu flow. It speaks a different line for KoalaByte Blue Lab Mode versus Koala
Konnect / External Adaptor Mode.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

PREBOOT_STATE_PATH = Path("logs/preboot_mode_selection.json")
DONGLE_MODE_STATE_PATH = Path("logs/dongle_mode_state.json")
WELCOME_LOG = Path("logs/killerkoala/boot_welcome_alerts.jsonl")

MODE_TITLES = {
    "koalabyte_lab": "KoalaByte Blue Lab Mode",
    "koala_konnect": "External Adaptor Mode",
}

KILLERKOALA_BOOT_WELCOME_LINES = {
    "koalabyte_lab": "G'day mate, KillerKoala is online. Lab Mode is loaded — clean scope, clean signals. Select a menu item to get started.",
    "koala_konnect": "G'day mate, KillerKoala is online. External adaptor mode is loaded — plug in the dongle and drive the stack. Select a menu item to get started.",
    "unknown": "G'day mate, KillerKoala is online. Mode status is unclear, but the menu is ready. Select a menu item to get started.",
}


def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def resolve_boot_mode(
    *,
    mode: Optional[str] = None,
    preboot_state_path: Path = PREBOOT_STATE_PATH,
    dongle_state_path: Path = DONGLE_MODE_STATE_PATH,
) -> tuple[str, str]:
    """Resolve the active boot mode and describe where it came from."""

    if mode:
        normalized = mode.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"lab", "koalabyte", "koalabyte_blue_lab"}:
            return "koalabyte_lab", "argument"
        if normalized in {"konnect", "adapter", "external_adapter", "external_adaptor", "koala_konnect"}:
            return "koala_konnect", "argument"
        if normalized in MODE_TITLES:
            return normalized, "argument"
        return "unknown", "argument"

    preboot = _read_json(preboot_state_path)
    selected = str(preboot.get("selected_mode", "")).strip()
    if selected in MODE_TITLES:
        return selected, str(preboot.get("selection_source", "preboot_state")) or "preboot_state"

    dongle = _read_json(dongle_state_path)
    active = str(dongle.get("active_mode", "")).strip()
    if active in MODE_TITLES:
        return active, "dongle_mode_state"

    return "unknown", "fallback"


def _resolve_tts_command(preferred: Optional[str] = None) -> Optional[str]:
    candidates = [preferred] if preferred else []
    candidates.extend(["espeak-ng", "espeak", "say"])
    for candidate in candidates:
        if candidate and shutil.which(candidate):
            return candidate
    return None


def _tts_args(command: str, line: str) -> list[str]:
    name = Path(command).name.lower()
    if name in {"espeak-ng", "espeak"}:
        return [command, "-v", "en-au", "-p", "28", "-s", "135", "-a", "180", line]
    if name == "say":
        return [command, "-v", "Lee", line]
    return [command, line]


def build_welcome_line(mode_key: str) -> str:
    return KILLERKOALA_BOOT_WELCOME_LINES.get(mode_key, KILLERKOALA_BOOT_WELCOME_LINES["unknown"])


def speak_boot_welcome(
    *,
    mode: Optional[str] = None,
    tts_enabled: Optional[bool] = None,
    tts_command: Optional[str] = None,
    welcome_log: str | Path = WELCOME_LOG,
) -> dict:
    mode_key, source = resolve_boot_mode(mode=mode)
    line = build_welcome_line(mode_key)
    payload = {
        "action": "killerkoala_boot_welcome",
        "event": "boot_welcome",
        "mode": mode_key,
        "mode_title": MODE_TITLES.get(mode_key, "Unknown Mode"),
        "mode_source": source,
        "line": line,
        "voice_profile": "Australian male, gruff cyberpunk lab companion",
        "timestamp": time.time(),
    }
    _append_jsonl(Path(welcome_log), payload)
    print(f"killerkoala boot welcome [{payload['mode_title']}]: {line}")

    enabled = tts_enabled if tts_enabled is not None else os.environ.get("KOALABYTE_TTS", "1") != "0"
    command = _resolve_tts_command(tts_command) if enabled else None
    if command:
        try:
            subprocess.run(_tts_args(command, line), check=False, timeout=8)
        except Exception:
            pass
    return payload


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="KillerKoala mode-aware boot welcome alert")
    parser.add_argument("--mode", default=None, help="Override mode: koalabyte_lab/lab or koala_konnect/external adaptor")
    parser.add_argument("--no-tts", action="store_true", help="Print/log the alert without spoken audio")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON after the alert")
    args = parser.parse_args(argv)

    payload = speak_boot_welcome(mode=args.mode, tts_enabled=not args.no_tts)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
