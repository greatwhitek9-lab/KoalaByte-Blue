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
import math
import os
import select
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from .menu_theme import DEFAULT_JUNGLE_MENU_THEME, JungleMenuUnavailable, _import_pygame, _pick_font

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


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


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

    return CyberPetState(contentment, max(state.total_observations_seen, stats.observation_count), stats.observation_count, last_new_data_time, direction, next_pos, mood, boomerang_throws, now), delta, should_grumble, mood


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


def run_terminal(
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


def _draw_leaf(pygame, screen, x: int, y: int, scale: float = 1.0, angle: float = 0.0) -> None:
    color = (92, 186, 102)
    highlight = (166, 246, 163)
    rx, ry = int(11 * scale), int(5 * scale)
    rect = pygame.Rect(x - rx, y - ry, rx * 2, ry * 2)
    pygame.draw.ellipse(screen, color, rect)
    pygame.draw.line(screen, highlight, (x - rx + 2, y), (x + rx - 2, y), max(1, int(1.5 * scale)))


def _draw_branch(pygame, screen, w: int, h: int) -> tuple[int, int, int, int]:
    y = int(h * 0.52)
    start = int(w * 0.04)
    end = int(w * 0.96)
    for thickness, color in [(26, (61, 38, 18)), (18, (102, 70, 34)), (8, (151, 108, 54))]:
        pygame.draw.line(screen, color, (start, y), (end, y), thickness)
    for i in range(18):
        x = start + int((end - start) * i / 17)
        leaf_y = y - 28 - int(9 * math.sin(i))
        _draw_leaf(pygame, screen, x, leaf_y, 1.1 + (i % 3) * 0.18)
    return start, y, end, y


def _draw_koala(pygame, screen, x: int, y: int, scale: float, mood: str) -> None:
    fur = (145, 152, 154)
    fur_dark = (78, 82, 84)
    ear_inner = (220, 170, 185)
    nose = (26, 25, 27)
    eye = (40, 255, 120) if mood != "cranky boomerang toss" else (255, 142, 46)
    r = int(26 * scale)
    ear_r = int(17 * scale)
    pygame.draw.circle(screen, fur_dark, (x - r, y - r), ear_r)
    pygame.draw.circle(screen, fur_dark, (x + r, y - r), ear_r)
    pygame.draw.circle(screen, ear_inner, (x - r, y - r), int(ear_r * 0.55))
    pygame.draw.circle(screen, ear_inner, (x + r, y - r), int(ear_r * 0.55))
    pygame.draw.circle(screen, fur, (x, y), r)
    pygame.draw.circle(screen, eye, (x - int(9 * scale), y - int(5 * scale)), int(3.5 * scale))
    pygame.draw.circle(screen, eye, (x + int(9 * scale), y - int(5 * scale)), int(3.5 * scale))
    pygame.draw.ellipse(screen, nose, pygame.Rect(x - int(6 * scale), y, int(12 * scale), int(10 * scale)))
    pygame.draw.arc(screen, nose, pygame.Rect(x - int(12 * scale), y + int(5 * scale), int(24 * scale), int(16 * scale)), 0.15, math.pi - 0.15, max(1, int(2 * scale)))


def _draw_boomerang(pygame, screen, x: int, y: int, tick: int) -> None:
    radius = 36
    bx = x + int(math.cos(tick / 6.0) * radius)
    by = y - 42 + int(math.sin(tick / 6.0) * 18)
    points = [(bx - 22, by + 8), (bx, by - 5), (bx + 22, by + 8), (bx + 8, by + 14), (bx, by + 5), (bx - 8, by + 14)]
    pygame.draw.polygon(screen, (213, 149, 58), points)
    pygame.draw.lines(screen, (255, 218, 116), False, points[:3], 3)


def _draw_panel(pygame, screen, font, small_font, state: CyberPetState, stats: EucalyptusStats, delta: int, w: int, h: int) -> None:
    panel = pygame.Rect(int(w * 0.05), int(h * 0.69), int(w * 0.90), int(h * 0.24))
    pygame.draw.rect(screen, (6, 28, 20), panel, border_radius=22)
    pygame.draw.rect(screen, (116, 236, 127), panel, 3, border_radius=22)
    title = font.render("KOALAGOTCHI STATUS", True, (231, 248, 158))
    screen.blit(title, (panel.x + 20, panel.y + 12))
    bar = pygame.Rect(panel.x + 22, panel.y + 56, int((panel.w - 44) * state.contentment / 100), 24)
    bar_back = pygame.Rect(panel.x + 22, panel.y + 56, panel.w - 44, 24)
    pygame.draw.rect(screen, (30, 74, 45), bar_back, border_radius=12)
    pygame.draw.rect(screen, (119, 255, 107), bar, border_radius=12)
    pygame.draw.rect(screen, (221, 255, 170), bar_back, 2, border_radius=12)
    rows = [
        f"Contentment: {state.contentment}%   Mood: {state.mood}",
        f"Passive observations: {stats.observation_count}   New Bluetooth leaves: {delta}",
        f"Files watched: {stats.files_seen}   Boomerang throws: {state.boomerang_throws}",
    ]
    for idx, row in enumerate(rows):
        text = small_font.render(row, True, (204, 247, 202))
        screen.blit(text, (panel.x + 22, panel.y + 90 + idx * 24))


def run_graphical(
    *,
    capture_dirs: Iterable[Path] = DEFAULT_CAPTURE_DIRS,
    state_path: Path = DEFAULT_STATE_PATH,
    event_log: Path = DEFAULT_EVENT_LOG,
    idle_seconds: float = DEFAULT_IDLE_SECONDS,
    tick_seconds: float = DEFAULT_TICK_SECONDS,
    fullscreen: bool = True,
    width: int = 800,
    height: int = 480,
    fps: int = 30,
) -> int:
    pygame = _import_pygame()
    pygame.init()
    flags = pygame.FULLSCREEN if fullscreen else 0
    screen = pygame.display.set_mode((0, 0), flags) if fullscreen else pygame.display.set_mode((width, height), flags)
    pygame.display.set_caption("KoalaByte Blue - Eucalyptus Mode Koalagotchi")
    clock = pygame.time.Clock()
    w, h = screen.get_size()
    title_font = _pick_font(pygame, DEFAULT_JUNGLE_MENU_THEME.font_family, max(26, min(56, int(w * 0.05))), True)
    font = _pick_font(pygame, DEFAULT_JUNGLE_MENU_THEME.item_font_family, max(18, min(32, int(w * 0.030))), True)
    small_font = pygame.font.SysFont("dejavusans", max(13, min(22, int(w * 0.020))), bold=True)
    stats = read_eucalyptus_stats(capture_dirs)
    state = load_state(state_path, stats)
    last_tick = 0.0
    delta = 0
    tick = 0

    while True:
        now = time.time()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 0
            if event.type == pygame.KEYDOWN and event.key in {pygame.K_q, pygame.K_ESCAPE}:
                return 0

        if now - last_tick >= max(0.25, tick_seconds):
            stats = read_eucalyptus_stats(capture_dirs)
            state, delta, should_grumble, mood = update_pet_state(state, stats, idle_seconds=idle_seconds, branch_width=max(40, w - 120))
            save_state(state, state_path)
            append_event({
                "action": ACTION_NAME,
                "event": "graphical_tick",
                "observation_count": stats.observation_count,
                "delta": delta,
                "contentment": state.contentment,
                "mood": mood,
                "boomerang_throws": state.boomerang_throws,
                "timestamp": state.updated_at,
                "safety": "Eucalyptus Mode is a passive Bluetooth log visualization; no pairing/probing/disruption is started here",
            }, event_log)
            if delta > 0:
                speak_line("Nom nom. KillerKoala is eating Bluetooth eucalyptus data, mate.")
            elif should_grumble:
                line = DORMANT_GRUMBLES[state.boomerang_throws % len(DORMANT_GRUMBLES)]
                speak_line(line)
            last_tick = now

        for y in range(h):
            shade = int(18 + 34 * y / max(1, h))
            pygame.draw.line(screen, (2, shade, 20), (0, y), (w, y))
        title = title_font.render("EUCALYPTUS MODE", True, (174, 255, 121))
        subtitle = small_font.render("Koalagotchi always-on Bluetooth scanner + logger", True, (109, 214, 255))
        screen.blit(title, (int(w * 0.05), int(h * 0.04)))
        screen.blit(subtitle, (int(w * 0.055), int(h * 0.04) + title.get_height() + 4))
        pygame.draw.rect(screen, (85, 236, 110), pygame.Rect(16, 16, w - 32, h - 32), 4, border_radius=22)
        start_x, branch_y, end_x, _ = _draw_branch(pygame, screen, w, h)
        travel = max(1, end_x - start_x - 90)
        koala_x = start_x + 45 + int((state.position / max(1, w - 120)) * travel)
        koala_y = branch_y - 48
        _draw_koala(pygame, screen, koala_x, koala_y, 1.25, state.mood)
        if delta > 0 or state.mood.startswith("eating"):
            for i in range(min(6, max(1, delta))):
                _draw_leaf(pygame, screen, koala_x + 38 + i * 16, koala_y + 8 + (i % 2) * 10, 1.1)
        if state.mood == "cranky boomerang toss":
            _draw_boomerang(pygame, screen, koala_x + 60, koala_y, tick)
        speech = "Nom nom, Bluetooth eucalyptus snack." if delta > 0 else "Oi! Three minutes dry. Chuckin' the boomerang, mate." if state.mood == "cranky boomerang toss" else "Patrolling the branch for passive BLE leaves."
        bubble = pygame.Rect(int(w * 0.48), int(h * 0.16), int(w * 0.45), int(h * 0.16))
        pygame.draw.rect(screen, (245, 238, 165), bubble, border_radius=24)
        pygame.draw.rect(screen, (42, 112, 55), bubble, 3, border_radius=24)
        for idx, chunk in enumerate([speech[:48], speech[48:96]]):
            if chunk:
                screen.blit(small_font.render(chunk, True, (21, 52, 29)), (bubble.x + 18, bubble.y + 18 + idx * 24))
        _draw_panel(pygame, screen, font, small_font, state, stats, delta, w, h)
        safety = small_font.render("Passive Eucalyptus log visualization only. Press Q to return.", True, (184, 222, 192))
        screen.blit(safety, (int(w * 0.05), h - 34))
        pygame.display.flip()
        tick += 1
        clock.tick(fps)


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Eucalyptus Mode: Koalagotchi always-on Bluetooth scanner and logger screen")
    parser.add_argument("--capture-dir", action="append", default=[], help="Directory to watch for passive Eucalyptus Bluetooth logs. May be repeated.")
    parser.add_argument("--idle-seconds", type=float, default=DEFAULT_IDLE_SECONDS, help="Seconds without new observations before contentment drops and boomerang grumbles begin.")
    parser.add_argument("--tick-seconds", type=float, default=DEFAULT_TICK_SECONDS, help="Screen refresh interval.")
    parser.add_argument("--terminal", action="store_true", help="Use terminal renderer instead of full-color graphical renderer.")
    parser.add_argument("--windowed", action="store_true", help="Run graphical mode in a window instead of fullscreen.")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--once", action="store_true", help="Render one terminal frame and exit; used by smoke checks.")
    args = parser.parse_args(argv)
    capture_dirs = [Path(item) for item in args.capture_dir] if args.capture_dir else DEFAULT_CAPTURE_DIRS
    if args.terminal or args.once:
        return run_terminal(capture_dirs=capture_dirs, idle_seconds=args.idle_seconds, tick_seconds=args.tick_seconds, once=args.once)
    try:
        return run_graphical(capture_dirs=capture_dirs, idle_seconds=args.idle_seconds, tick_seconds=args.tick_seconds, fullscreen=not args.windowed, width=args.width, height=args.height)
    except JungleMenuUnavailable as exc:
        print(f"Full-color Eucalyptus Mode unavailable, falling back to terminal renderer: {exc}")
        return run_terminal(capture_dirs=capture_dirs, idle_seconds=args.idle_seconds, tick_seconds=args.tick_seconds)


if __name__ == "__main__":
    raise SystemExit(run_cli())
