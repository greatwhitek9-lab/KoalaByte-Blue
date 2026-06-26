from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .killerkoala_vocabulary import rank_for_xp
from .menu_catalog import MAIN_MENU_ITEMS, SUBMENU_ITEMS, all_menu_entries, submenu_name_from_command, submenu_title
from .menu_ui import MenuItem

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WAKE_WORD = "killerkoala"
LAUNCH_VERBS = {"run", "open"}
DEFAULT_MENU_VOICE_DIR = Path("logs/menu_voice")


@dataclass(frozen=True)
class MenuVoiceMatch:
    phrase: str
    normalized_phrase: str
    wake_word_detected: bool
    verb: Optional[str]
    requested_item: Optional[str]
    menu: str
    label: str
    command: str
    group: str
    description: str
    is_submenu: bool
    submenu: str
    alias: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _entry_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in MAIN_MENU_ITEMS:
        rows.append({"menu": "main", **entry})
    for menu_name, entries in SUBMENU_ITEMS.items():
        for entry in entries:
            rows.append({"menu": menu_name, **entry})
    return rows


def _aliases_for_entry(entry: dict[str, Any]) -> set[str]:
    label = str(entry.get("label", ""))
    command = str(entry.get("command", ""))
    submenu = submenu_name_from_command(command)
    aliases = {
        label,
        command,
        command.replace("_", " ").replace("-", " ").replace("/", " "),
        label.replace("/", " "),
    }
    if submenu:
        aliases.add(submenu)
        aliases.add(submenu.replace("_", " "))
        aliases.add(submenu_title(submenu))
        aliases.add(f"{submenu_title(submenu)} menu")
    aliases.add(f"{label} menu")
    return {_normalize(alias) for alias in aliases if _normalize(alias)}


def build_menu_voice_manifest() -> dict[str, Any]:
    entries = []
    for entry in _entry_rows():
        command = str(entry.get("command", ""))
        enabled = bool(entry.get("enabled", True))
        if not enabled:
            continue
        entries.append(
            {
                "menu": str(entry.get("menu", "main")),
                "group": str(entry.get("group", "")),
                "label": str(entry.get("label", "")),
                "command": command,
                "description": str(entry.get("description", "")),
                "is_submenu": bool(submenu_name_from_command(command)),
                "submenu": submenu_name_from_command(command),
                "voice_examples": [
                    f"{WAKE_WORD} run {entry.get('label', '')}",
                    f"{WAKE_WORD} open {entry.get('label', '')}",
                    f"{WAKE_WORD} run {command.replace('_', ' ')}",
                ],
                "aliases": sorted(_aliases_for_entry(entry)),
            }
        )
    return {
        "wake_word": WAKE_WORD,
        "launch_verbs": sorted(LAUNCH_VERBS),
        "syntax": [
            "killerkoala run <menu item or command>",
            "killerkoala open <menu item or command>",
        ],
        "entry_count": len(entries),
        "entries": entries,
    }


def parse_menu_voice_launch(phrase: str, require_wake_word: bool = True) -> Optional[MenuVoiceMatch]:
    normalized = _normalize(phrase)
    wake_word_detected = WAKE_WORD in normalized.split()
    if require_wake_word and not wake_word_detected:
        return None

    working = normalized
    if wake_word_detected:
        tokens = working.split()
        try:
            wake_index = tokens.index(WAKE_WORD)
            working = " ".join(tokens[wake_index + 1:]).strip()
        except ValueError:
            working = working.replace(WAKE_WORD, " ").strip()

    parts = working.split(maxsplit=1)
    if len(parts) < 2 or parts[0] not in LAUNCH_VERBS:
        return None
    verb, requested = parts[0], parts[1].strip()
    requested_norm = _normalize(requested)
    if not requested_norm:
        return None

    best: Optional[tuple[int, dict[str, Any], str]] = None
    for entry in _entry_rows():
        if not bool(entry.get("enabled", True)):
            continue
        for alias in _aliases_for_entry(entry):
            score = 0
            if requested_norm == alias:
                score = 1000 + len(alias)
            elif requested_norm in alias or alias in requested_norm:
                score = 500 + min(len(alias), len(requested_norm))
            if score and (best is None or score > best[0]):
                best = (score, entry, alias)

    if best is None:
        return None

    _score, entry, alias = best
    command = str(entry.get("command", ""))
    submenu = submenu_name_from_command(command)
    return MenuVoiceMatch(
        phrase=phrase,
        normalized_phrase=normalized,
        wake_word_detected=wake_word_detected,
        verb=verb,
        requested_item=requested,
        menu=str(entry.get("menu", "main")),
        label=str(entry.get("label", "")),
        command=command,
        group=str(entry.get("group", "")),
        description=str(entry.get("description", "")),
        is_submenu=bool(submenu),
        submenu=submenu,
        alias=alias,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _voice_result(
    *,
    status: str,
    match: MenuVoiceMatch,
    started_at: float,
    ended_at: float,
    xp_before: int,
    xp_after: int,
    xp_reward: int,
    companion_line: str,
    artifacts: dict[str, str],
    details: dict[str, Any],
    error: Optional[str] = None,
):
    from .killerkoala_voice_control import VoiceExecutionResult

    return VoiceExecutionResult(
        status=status,
        module_key="menu_voice_launch",
        module_title="Menu Voice Launcher",
        phrase=match.phrase,
        started_at=started_at,
        ended_at=ended_at,
        xp_before=xp_before,
        xp_after=xp_after,
        xp_reward=xp_reward,
        rank_before=rank_for_xp(xp_before),
        rank_after=rank_for_xp(xp_after),
        companion_line=companion_line,
        artifacts=artifacts,
        safety={
            "authorized_lab_use_only": True,
            "same_handler_path_as_touch_keyboard_and_gpio_menu": True,
            "disabled_menu_items_blocked": True,
            "wake_word_required": True,
            "launch_verbs": sorted(LAUNCH_VERBS),
        },
        details=details,
        error=error,
    )


def execute_menu_voice_launch(match: MenuVoiceMatch, output_dir: Path = DEFAULT_MENU_VOICE_DIR, xp_path: Path | None = None):
    from .killerkoala_voice_control import KillerKoalaXPState, load_xp_state, save_xp_state
    from scripts.run_menu_screen import make_menu, open_submenu, write_action_payload

    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    xp_state: KillerKoalaXPState = load_xp_state(xp_path) if xp_path is not None else KillerKoalaXPState(xp=0, rank=rank_for_xp(0), updated_at=time.time())
    xp_before = xp_state.xp
    artifacts: dict[str, str] = {}
    details: dict[str, Any] = {"match": asdict(match)}
    status = "success"
    error: Optional[str] = None

    try:
        menu = make_menu()
        if match.is_submenu:
            opened = open_submenu(menu, match.command)
            if not opened:
                raise RuntimeError(f"submenu target not available: {match.command}")
            payload = {
                "timestamp": started,
                "type": "menu_voice_open_submenu",
                "status": "opened",
                "voice_phrase": match.phrase,
                "wake_word": WAKE_WORD,
                "verb": match.verb,
                "label": match.label,
                "command": match.command,
                "submenu": match.submenu,
                "menu": match.menu,
            }
            path = output_dir / f"menu_voice_open_{match.submenu}_{int(started)}.json"
            _write_json(path, payload)
            artifacts["menu_voice_action"] = str(path)
            details["menu_action"] = payload
        else:
            handler = getattr(menu, "_handlers", {}).get(match.command)
            if handler is None:
                raise RuntimeError(f"no menu handler registered for command: {match.command}")
            item = MenuItem(label=match.label, command=match.command, description=match.description, enabled=True, group=match.group)
            handler(item)
            payload = {
                "timestamp": started,
                "type": "menu_voice_run_leaf",
                "status": "routed",
                "voice_phrase": match.phrase,
                "wake_word": WAKE_WORD,
                "verb": match.verb,
                "label": match.label,
                "command": match.command,
                "menu": match.menu,
                "group": match.group,
            }
            path = write_action_payload(item, payload)
            artifacts["menu_voice_action"] = str(path)
            details["menu_action"] = payload
    except Exception as exc:
        status = "error"
        error = str(exc)

    xp_reward = 1 if status == "success" else 0
    if xp_path is not None:
        if status == "success":
            xp_state.xp += xp_reward
            xp_state.successful_modules += 1
            xp_state.last_module = match.label
        else:
            xp_state.failed_modules += 1
        save_xp_state(xp_state, xp_path)
    ended = time.time()
    companion_line = f"Opening {match.label}, mate." if status == "success" else f"Could not open {match.requested_item}: {error}"
    result = _voice_result(
        status=status,
        match=match,
        started_at=started,
        ended_at=ended,
        xp_before=xp_before,
        xp_after=xp_state.xp,
        xp_reward=xp_reward,
        companion_line=companion_line,
        artifacts=artifacts,
        details=details,
        error=error,
    )
    result_path = output_dir / f"menu_voice_result_{int(started)}.json"
    _write_json(result_path, asdict(result))
    result.artifacts["voice_result"] = str(result_path)
    return result


def route_menu_voice_launch(phrase: str, output_dir: Path = DEFAULT_MENU_VOICE_DIR, xp_path: Path | None = None, require_wake_word: bool = True):
    match = parse_menu_voice_launch(phrase, require_wake_word=require_wake_word)
    if match is None:
        return None
    return execute_menu_voice_launch(match, output_dir=output_dir, xp_path=xp_path)
