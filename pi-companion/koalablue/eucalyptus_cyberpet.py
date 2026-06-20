#!/usr/bin/env python3
"""Eucalyptus Mode Koalagotchi screen.

Eucalyptus Mode is a Koalagotchi-style always-on Bluetooth scanner/logger
companion screen. It does not start pairing, connection, probing, disruption,
or access workflows. It reads local passive Eucalyptus Bluetooth/BLE capture
logs and turns observation activity into KillerKoala movement, eating,
contentment, and idle grumbling.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import select
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

ACTION_NAME = "Eucalyptus Mode"
DESCRIPTION = "Koalagotchi always-on Bluetooth scanner and logger screen for passive Eucalyptus observations."
DEFAULT_CAPTURE_DIRS = [Path("/blecaptures"), Path("logs/eucalyptus"), Path("logs/koala_bluez"), Path("/blecaptures/koala_kapture")]
DEFAULT_STATE_PATH = Path("logs/eucalyptus_mode/state.json")
DEFAULT_EVENT_LOG = Path("logs/eucalyptus_mode/events.jsonl")
DEFAULT_IDLE_SECONDS = 180.0
DEFAULT_TICK_SECONDS = 1.0
MAX_CONTENTMENT = 100
MIN_CONTENTMENT = 0

DORMANT_GRUMBLES = [
    "Oi, ya drongo, the air's drier than a dead gumleaf. Give me some Bluetooth tucker!",
    "Bloody quiet out here, mate. KillerKoala's chuckin' the boomerang till the blue snacks show up.",
    "Not a single Bluetooth nibble in three minutes. Fair dinkum, this branch is boring.",
]


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


@dataclass(frozen=True)
class EucalyptusStats:
    observation_count: int
    newest_mtime: float
    files_seen: int
    source_dirs: list[str]


@dataclass(frozen=True)
class CyberPetState:
    contentment: int
    total_observations_seen: int
    last_observation_count: int
    last_new_data_time: float
    direction: int
    position: int
    mood: str
    boomerang_throws: int
    updated_at: float


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _count_json_payload(payload: object) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("observations", "devices", "records", "results", "events"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return 1 if payload else 0
    return 0


def _count_file(path: Path) -> int:
    suffix = path.suffix.lower()
    try:
        if suffix == ".jsonl":
            return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())
        if suffix == ".json":
            return _count_json_payload(_read_json(path))
        if suffix == ".csv":
            with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                rows = list(csv.reader(handle))
            return max(0, len(rows) - 1) if rows else 0
        if suffix in {".log", ".txt", ".ndjson"}:
            return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())
    except Exception:
        return 0
    return 0


def _iter_capture_files(capture_dirs: Iterable[Path]) -> Iterable[Path]:
    allowed = {".jsonl", ".json", ".csv", ".log", ".txt", ".ndjson"}
    for directory in capture_dirs:
        try:
            if not directory.exists() or not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if path.is_file() and path.suffix.lower() in allowed:
                    yield path
        except PermissionError:
            continue


def read_eucalyptus_stats(capture_dirs: Iterable[Path] = DEFAULT_CAPTURE_DIRS) -> EucalyptusStats:
    dirs = [Path(item) for item in capture_dirs]
    total = 0
    newest = 0.0
    files = 0
    for path in _iter_capture_files(dirs):
        files += 1
        total += _count_file(path)
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            pass
    return EucalyptusStats(total, newest, files, [str(path) for path in dirs])


def _default_state(stats: EucalyptusStats) -> CyberPetState:
    now = time.time()
    return CyberPetState(50, stats.observation_count, stats.observation_count, stats.newest_mtime or now, 1, 0, "scouting", 0, now)


def load_state(path: Path, stats: EucalyptusStats) -> CyberPetState:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return _default_state(stats)
    return CyberPetState(
        contentment=max(MIN_CONTENTMENT, min(MAX_CONTENTMENT, _safe_int(payload.get("contentment"), 50))),
        total_observations_seen=_safe_int(payload.get("total_observations_seen"), stats.observation_count),
        last_observation_count=_safe_int(payload.get("last_observation_count"), stats.observation_count),
        last_new_data_time=float(payload.get("last_new_data_time", stats.newest_mtime or time.time())),
        direction=1 if _safe_int(payload.get("direction"), 1) >= 0 else -1,
        position=max(0, _safe_int(payload.get("position"), 0)),
        mood=str(payload.get("mood", "scouting")),
        boomerang_throws=_safe_int(payload.get("boomerang_throws"), 0),
        updated_at=float(payload.get("updated_at", time.time())),
    )


def save_state(state: CyberPetState, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")


def append_event(event: dict, path: Path = DEFAULT_EVENT_LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


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
        return [command, "-v", "en-au", "-p", "28", "-s", "138", "-a", "170", line]
    if name == "say":
        return [command, "-v", "Lee", line]
    return [command, line]


def speak_line(line: str, *, tts_enabled: Optional[bool] = None, tts_command: Optional[str] = None) -> None:
    enabled = tts_enabled if tts_enabled is not None else os.environ.get("KOALABYTE_TTS", "1") != "0"
    command = _resolve_tts_command(tts_command) if enabled else None
    if command:
        try:
            subprocess.run(_tts_args(command, line), check=False, timeout=8)
        except Exception:
            pass


def update_pet_state(
    state: CyberPetState,
    stats: EucalyptusStats,
    *,
    idle_seconds: float = DEFAULT_IDLE_SECONDS,
    branch_width: int = 60,
) -> tuple[CyberPetState, int, bool, str]:
    now = time.time()
    delta = max(0, stats.observation_count - state.last_observation_count)
    idle_for = now - (state.last_new_data_time or now)
    contentment = state.contentment
    mood = state.mood
    boomerang_throws = state.boomerang_throws
    last_new_data_time = state.last_new_data_time
    should_grumble = False

    if delta > 0:
        contentment = min(MAX_CONTENTMENT, contentment + min(20, 4 + delta * 3))
        mood = "eating eucalyptus Bluetooth leaves"
        last_new_data_time = now
    elif idle_for >= idle_seconds:
        contentment = max(MIN_CONTENTMENT, contentment - 2)
        mood = "cranky boomerang toss"
        boomerang_throws += 1
        should_grumble = boomerang_throws == 1 or boomerang_throws % 30 == 0
    else:
        contentment = max(MIN_CONTENTMENT, contentment - 1 if idle_for > 60 else contentment)
        mood = "patrolling the gum branch"

    next_pos = state.position + state.direction
    direction = state.direction
    max_pos = max(0, branch_width - 7)
    if next_pos >= max_pos:
        next_pos = max_pos
        direction = -1
    elif next_pos <= 0:
        next_pos = 0
        direction = 1

    next_state = CyberPetState(
        contentment=contentment,
        total_observations_seen=max(state.total_observations_seen, stats.observation_count),
        last_observation_count=stats.observation_count,
        last_new_data_time=last_new_data_time,
        direction=direction,
        position=next_pos,
        mood=mood,
        boomerang_throws=boomerang_throws,
        updated_at=now,
    )
    return next_state, delta, should_grumble, mood


def _bar(value: int, width: int = 24) -> str:
    filled = int(round(width * max(MIN_CONTENTMENT, min(MAX_CONTENTMENT, value)) / MAX_CONTENTMENT))
    return "█" * filled + "░" * (width - filled)


def render_tamagotchi_screen(state: CyberPetState, stats: EucalyptusStats, *, delta: int, width: int = 72) -> str:
    width = max(48, min(96, width))
    branch_width = width - 8
    pos = max(0, min(branch_width - 7, state.position))
    koala = "ʕ•ᴥ•ʔ"
    leaves = "🍃" * min(5, max(0, delta)) if delta else "🍃" if state.mood.startswith("eating") else ""
    boomerang = "  🪃" if state.mood == "cranky boomerang toss" else ""
    branch = "═" * branch_width
    koala_line = " " * pos + koala + leaves + boomerang
    speech = (
        "Nom nom, Bluetooth eucalyptus snack." if delta > 0 else
        "Oi! Three minutes dry. Chuckin' the boomerang, mate." if state.mood == "cranky boomerang toss" else
        "Patrolling the branch for passive BLE leaves."
    )
    title = "EUCALYPTUS MODE // KOALAGOTCHI ALWAYS-ON BLUETOOTH"
    border = "╔" + "═" * (width - 2) + "╗"
    footer = "╚" + "═" * (width - 2) + "╝"
    lines = [
        border,
        "║" + title.center(width - 2) + "║",
        "╠" + "═" * (width - 2) + "╣",
        "║" + koala_line[: width - 2].ljust(width - 2) + "║",
        "║" + branch[: width - 2].ljust(width - 2) + "║",
        "║" + ("  branch stretches end-to-end; KillerKoala patrols for BLE leaves"[: width - 2]).ljust(width - 2) + "║",
        "╠" + "═" * (width - 2) + "╣",
        "║" + f"Contentment [{_bar(state.contentment)}] {state.contentment:3d}%".ljust(width - 2) + "║",
        "║" + f"Passive observations: {stats.observation_count}   New snack count: {delta}".ljust(width - 2) + "║",
        "║" + f"Files watched: {stats.files_seen}   Boomerang throws: {state.boomerang_throws}".ljust(width - 2) + "║",
        "║" + f"Mood: {state.mood}".ljust(width - 2) + "║",
        "║" + f"KillerKoala says: {speech}"[: width - 2].ljust(width - 2) + "║",
        "╠" + "═" * (width - 2) + "╣",
        "║" + "Safety: Eucalyptus passive Bluetooth scanner/logger status only.".ljust(width - 2) + "║",
        "║" + "Press q then Enter to quit back to the KoalaByte menu.".ljust(width - 2) + "║",
        footer,
    ]
    return "\n".join(lines)


def _screen_width(default: int = 72) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


def _input_ready() -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(ready)
    except Exception:
        return False


def run_interactive(
    *,
    capture_dirs: Iterable[Path] = DEFAULT_CAPTURE_DIRS,
    state_path: Path = DEFAULT_STATE_PATH,
    event_log: Path = DEFAULT_EVENT_LOG,
    idle_seconds: float = DEFAULT_IDLE_SECONDS,
    tick_seconds: float = DEFAULT_TICK_SECONDS,
    once: bool = False,
) -> int:
    stats = read_eucalyptus_stats(capture_dirs)
    state = load_state(state_path, stats)
    print("KillerKoala Eucalyptus Mode is online. Watching passive Bluetooth logs only.")
    while True:
        stats = read_eucalyptus_stats(capture_dirs)
        state, delta, should_grumble, mood = update_pet_state(state, stats, idle_seconds=idle_seconds, branch_width=max(40, _screen_width() - 8))
        save_state(state, state_path)
        append_event({
            "action": ACTION_NAME,
            "event": "tick",
            "observation_count": stats.observation_count,
            "delta": delta,
            "contentment": state.contentment,
            "mood": mood,
            "boomerang_throws": state.boomerang_throws,
            "timestamp": state.updated_at,
            "safety": "passive Eucalyptus Bluetooth log watcher; no pairing, probing, disruption, or access workflow",
        }, event_log)
        if delta > 0:
            speak_line("Nom nom. KillerKoala is eating Bluetooth eucalyptus data, mate.")
        elif should_grumble:
            line = DORMANT_GRUMBLES[state.boomerang_throws % len(DORMANT_GRUMBLES)]
            speak_line(line)
            append_event({"action": ACTION_NAME, "event": "dormant_grumble", "line": line, "timestamp": time.time()}, event_log)

        os.system("clear" if os.name != "nt" else "cls")
        print(render_tamagotchi_screen(state, stats, delta=delta, width=_screen_width()))
        if once:
            return 0
        if _input_ready():
            raw = sys.stdin.readline().strip().lower()
            if raw in {"q", "quit", "exit", "back", "menu"}:
                return 0
        time.sleep(max(0.1, tick_seconds))


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Eucalyptus Mode: Koalagotchi always-on Bluetooth scanner and logger screen")
    parser.add_argument("--capture-dir", action="append", default=[], help="Directory to watch for passive Eucalyptus Bluetooth logs. May be repeated.")
    parser.add_argument("--idle-seconds", type=float, default=DEFAULT_IDLE_SECONDS, help="Seconds without new observations before contentment drops and boomerang grumbles begin.")
    parser.add_argument("--tick-seconds", type=float, default=DEFAULT_TICK_SECONDS, help="Screen refresh interval.")
    parser.add_argument("--once", action="store_true", help="Render one frame and exit; used by smoke checks.")
    args = parser.parse_args(argv)
    capture_dirs = [Path(item) for item in args.capture_dir] if args.capture_dir else DEFAULT_CAPTURE_DIRS
    return run_interactive(capture_dirs=capture_dirs, idle_seconds=args.idle_seconds, tick_seconds=args.tick_seconds, once=args.once)


if __name__ == "__main__":
    raise SystemExit(run_cli())
