from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .killerkoala_hybrid_companion import companion_response
from .killerkoala_vocabulary import rank_for_xp


DEFAULT_XP_PATH = Path("logs/killerkoala/xp_state.json")
DEFAULT_OUTPUT_DIR = Path("logs/killerkoala_voice")
WAKE_WORD = "killerkoala"
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
DURATION_RE = re.compile(r"\b(\d{1,3})\s*(?:seconds?|secs?|s)\b", re.IGNORECASE)


@dataclass(frozen=True)
class VoiceModuleSpec:
    key: str
    title: str
    phrases: List[str]
    xp_reward: int
    event: str
    safe_scope: str
    owned_device_required: bool = False
    target_required: bool = False


@dataclass(frozen=True)
class VoiceMenuAction:
    command: str
    label: str
    group: str
    aliases: List[str]


@dataclass
class KillerKoalaXPState:
    xp: int = 0
    rank: str = "Noob"
    successful_modules: int = 0
    failed_modules: int = 0
    last_module: str = ""
    updated_at: float = 0.0


@dataclass
class ParsedVoiceCommand:
    raw_phrase: str
    normalized_phrase: str
    wake_word_detected: bool
    module_key: Optional[str]
    target: Optional[str] = None
    owned_device: bool = False
    raw_addresses: bool = False
    duration_seconds: Optional[int] = None
    menu_action: Optional[VoiceMenuAction] = None


@dataclass
class VoiceExecutionResult:
    status: str
    module_key: Optional[str]
    module_title: Optional[str]
    phrase: str
    started_at: float
    ended_at: float
    xp_before: int
    xp_after: int
    xp_reward: int
    rank_before: str
    rank_after: str
    companion_line: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    safety: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


VOICE_MODULES: Dict[str, VoiceModuleSpec] = {
    "bluez_manifest": VoiceModuleSpec("bluez_manifest", "KoalaByte Blue Outback Module Deck", ["module manifest", "bluez manifest", "outback module deck", "show modules"], 1, "bluez_status", "Write the local BlueZ module manifest."),
    "bluez_inventory": VoiceModuleSpec("bluez_inventory", "Gumleaf Gear Check", ["gumleaf gear check", "bluez inventory", "inventory", "check bluez tools", "gear check"], 3, "bluez_status", "List installed local BlueZ helper tools."),
    "bluez_status": VoiceModuleSpec("bluez_status", "Eucalyptus Bus Scout", ["eucalyptus bus scout", "bluez status", "adapter status", "controller status", "check bluetooth status", "suss the bluetooth stack", "give the radio a squiz"], 5, "bluez_status", "Collect local Bluetooth controller and adapter status."),
    "bluez_scan": VoiceModuleSpec("bluez_scan", "Dropbear Discovery Sweep", ["dropbear discovery sweep", "bluez scan", "bluetooth scan", "discovery sweep", "scan bluetooth", "give the air a squiz", "sweep the air", "sniff the gumtrees"], 10, "scan_complete", "Run bounded local Bluetooth discovery. Addresses are hashed unless raw logging is explicitly requested."),
    "bluez_monitor": VoiceModuleSpec("bluez_monitor", "Billabong HCI Watch", ["billabong hci watch", "bluez monitor", "hci monitor", "btmon", "monitor bluetooth"], 8, "bluez_status", "Run bounded local btmon capture for owned lab debugging."),
    "bluez_all_safe": VoiceModuleSpec("bluez_all_safe", "Kookaburra Safe Nest Run", ["kookaburra safe nest run", "safe nest run", "run all safe", "bluez all safe"], 12, "bluez_status", "Run BlueZ inventory, status, and bounded discovery with safe defaults."),
    "bluez_info": VoiceModuleSpec("bluez_info", "Joey Target Card", ["joey target card", "bluez info", "target card", "device info"], 5, "bluez_status", "Show target info only for an owned or written-scope device.", owned_device_required=True, target_required=True),
    "bluez_services": VoiceModuleSpec("bluez_services", "Treehouse Service Notes", ["treehouse service notes", "service notes", "browse services", "bluez services"], 5, "bluez_status", "Browse service notes only for an owned or written-scope device.", owned_device_required=True, target_required=True),
    "gatt_readiness": VoiceModuleSpec("gatt_readiness", "Gumnut GATT Readiness", ["gumnut gatt readiness", "gatt readiness", "gatt checklist", "owned gatt checklist"], 4, "bluez_status", "Write an owned-device GATT readiness checklist. Does not perform GATT writes.", owned_device_required=True, target_required=True),
    "koala_kapture": VoiceModuleSpec("koala_kapture", "Koala Kapture", ["koala kapture", "kapture", "capture ble", "capture metadata", "metadata capture", "bag the beacons", "save the signals"], 15, "capture_saved", "Run passive BLE metadata capture only."),
    "koala_kry": VoiceModuleSpec("koala_kry", "Koala Kry", ["koala kry", "kry", "offline replay", "replay metadata", "chew through the logs"], 5, "koala_kry", "Replay captured metadata offline only. No RF transmission."),
    "ear_tag_tx_lab": VoiceModuleSpec("ear_tag_tx_lab", "KoalaByte Lab", ["koalabyte lab", "koala byte lab", "ear tag tx lab", "ear tag", "lab beacon plan", "beacon plan"], 5, "ear_tag_tx_lab", "Write a synthetic owned-device BLE advertisement plan artifact."),
    "killerkoala_help": VoiceModuleSpec("killerkoala_help", "killerkoala Help", ["help", "what can you do", "list commands", "voice commands", "menu voice commands"], 1, "inquiry_help", "Show available voice-controlled modules and menu actions."),
}

BASE_MODULE_TO_MENU_COMMAND = {
    "bluez_manifest": ("koala_bluez_manifest", "Outback Module Deck", "Bluetooth Tools"),
    "bluez_inventory": ("koala_bluez_inventory", "Gumleaf Gear Check", "Bluetooth Tools"),
    "bluez_status": ("koala_bluez_status", "Eucalyptus Bus Scout", "Bluetooth Tools"),
    "bluez_scan": ("koala_bluez_scan", "Dropbear Discovery Sweep", "Bluetooth Tools"),
    "bluez_monitor": ("koala_bluez_monitor", "Billabong HCI Watch", "Bluetooth Tools"),
    "bluez_all_safe": ("koala_bluez_all_safe", "Kookaburra Safe Nest Run", "Bluetooth Tools"),
    "bluez_info": ("koala_bluez_info", "Joey Target Dossier", "Bluetooth Tools"),
    "bluez_services": ("koala_bluez_services", "Treehouse Service Trace", "Bluetooth Tools"),
    "gatt_readiness": ("koala_bluez_gatt_readiness", "Gumnut GATT Gatecheck", "Bluetooth Tools"),
    "koala_kapture": ("koala_kapture", "Koala Kapture", "Bluetooth Tools"),
    "koala_kry": ("koala_kry", "Koala Kry", "Bluetooth Tools"),
    "ear_tag_tx_lab": ("ear_tag_tx_lab", "KoalaByte Lab", "Bluetooth Tools"),
}

FLEXIBLE_BANTER_TRIGGERS = (
    "banter", "chat", "talk", "say something", "be cheeky", "surprise me", "what do you reckon", "give me some attitude"
)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def load_xp_state(path: Path = DEFAULT_XP_PATH) -> KillerKoalaXPState:
    if not path.exists():
        return KillerKoalaXPState(rank=rank_for_xp(0), updated_at=time.time())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        xp = int(payload.get("xp", 0))
        return KillerKoalaXPState(
            xp=xp,
            rank=rank_for_xp(xp),
            successful_modules=int(payload.get("successful_modules", 0)),
            failed_modules=int(payload.get("failed_modules", 0)),
            last_module=str(payload.get("last_module", "")),
            updated_at=float(payload.get("updated_at", time.time())),
        )
    except Exception:
        return KillerKoalaXPState(rank=rank_for_xp(0), updated_at=time.time())


def save_xp_state(state: KillerKoalaXPState, path: Path = DEFAULT_XP_PATH) -> None:
    state.rank = rank_for_xp(state.xp)
    state.updated_at = time.time()
    _write_json(path, asdict(state))


def _normalize_phrase(phrase: str) -> str:
    text = phrase.lower().replace("’", "'").replace("_", " ").replace("-", " ").replace("/", " ")
    text = re.sub(r"[^a-z0-9:+ '\s]", " ", text)
    return re.sub(r"\s+", " ", text.strip())


def _menu_aliases(label: str, command: str) -> List[str]:
    base = sorted({_normalize_phrase(label), _normalize_phrase(command), _normalize_phrase(command.replace(":", " "))})
    aliases: list[str] = []
    verbs = ["run", "start", "launch", "open", "select", "do", "execute", "activate"]
    for item in base:
        if item:
            aliases.append(item)
            aliases.extend([f"{verb} {item}" for verb in verbs])
            aliases.extend([f"menu {item}", f"action {item}"])
    return sorted(set(aliases), key=len, reverse=True)


def voice_menu_actions() -> List[VoiceMenuAction]:
    try:
        from .menu_catalog import leaf_menu_entries
    except Exception:
        return []
    actions: list[VoiceMenuAction] = []
    for entry in leaf_menu_entries():
        command = str(entry.get("command", "")).strip()
        label = str(entry.get("label", command)).strip()
        if not command or command == "quit":
            continue
        actions.append(VoiceMenuAction(command=command, label=label, group=str(entry.get("group", "")), aliases=_menu_aliases(label, command)))
    return actions


def _resolve_menu_action(working_phrase: str) -> Optional[VoiceMenuAction]:
    normalized = _normalize_phrase(working_phrase)
    best: Optional[VoiceMenuAction] = None
    best_len = 0
    for action in voice_menu_actions():
        for alias in action.aliases:
            if alias and (normalized == alias or alias in normalized):
                if len(alias) > best_len:
                    best = action
                    best_len = len(alias)
    return best


def module_manifest() -> Dict[str, Any]:
    menu_actions = voice_menu_actions()
    return {
        "wake_word": WAKE_WORD,
        "modules": {key: asdict(spec) for key, spec in sorted(VOICE_MODULES.items())},
        "menu_actions": [asdict(action) for action in menu_actions],
        "menu_action_count": len(menu_actions),
        "voice_menu_examples": [
            "killerkoala run Wi-Fi + BLE Survey",
            "killerkoala select T114 BLE Check",
            "killerkoala launch Eucalyptus GPS Trail",
            "killerkoala open Koala Kan Kommander",
        ],
        "companion": {
            "fast_default": "pi-companion/koalablue/killerkoala_vocabulary.py",
            "optional_flexible_banter": "pi-companion/koalablue/killerkoala_hybrid_companion.py",
            "llm_model_env": "KILLERKOALA_LLM_MODEL",
            "default_llm_model": "killerkoala-tinyllama:latest",
            "lora_training_doc": "docs/KILLERKOALA_LORA_TRAINING.md",
        },
        "safety": {
            "authorized_lab_use_only": True,
            "restricted_placeholder_enabled": False,
            "xp_awarded_on_success_only": True,
            "target_specific_modules_require_owned_device_phrase": True,
            "voice_activation_can_be_tested_with_typed_phrases": True,
            "all_enabled_menu_leaf_actions_voice_launchable": True,
            "manual_prompt_required": False,
        },
    }


def _extract_duration(phrase: str, default: int, minimum: int, maximum: int) -> int:
    match = DURATION_RE.search(phrase)
    if not match:
        return default
    return max(minimum, min(int(match.group(1)), maximum))


def _extract_target(phrase: str) -> Optional[str]:
    match = MAC_RE.search(phrase)
    return match.group(0).upper() if match else None


def _owned_device_ack(phrase: str) -> bool:
    owned_phrases = ["owned device", "owned lab", "authorized device", "authorised device", "in scope", "scope approved", "my device", "lab device"]
    return any(token in phrase for token in owned_phrases)


def _raw_addresses_ack(phrase: str) -> bool:
    return "raw address" in phrase or "show address" in phrase or "show mac" in phrase


def parse_voice_command(phrase: str, require_wake_word: bool = True) -> Optional[ParsedVoiceCommand]:
    normalized = _normalize_phrase(phrase)
    tokens = normalized.split()
    wake = WAKE_WORD in tokens
    if require_wake_word and not wake:
        return None
    working = normalized
    if wake:
        try:
            wake_index = tokens.index(WAKE_WORD)
            working = " ".join(tokens[wake_index + 1 :]).strip()
        except ValueError:
            working = normalized.replace(WAKE_WORD, "").strip()
    if not working:
        return ParsedVoiceCommand(phrase, normalized, wake, "killerkoala_help")
    menu_action = _resolve_menu_action(working)
    target = _extract_target(working)
    owned = _owned_device_ack(working)
    raw_addresses = _raw_addresses_ack(working)
    if menu_action is not None:
        return ParsedVoiceCommand(raw_phrase=phrase, normalized_phrase=normalized, wake_word_detected=wake, module_key="menu_action", menu_action=menu_action, target=target, owned_device=owned, raw_addresses=raw_addresses)
    for key, spec in VOICE_MODULES.items():
        if any(trigger in working for trigger in spec.phrases):
            return ParsedVoiceCommand(raw_phrase=phrase, normalized_phrase=normalized, wake_word_detected=wake, module_key=key, target=target, owned_device=owned, raw_addresses=raw_addresses, duration_seconds=_extract_duration(working, default=10, minimum=3, maximum=120))
    if any(trigger in working for trigger in FLEXIBLE_BANTER_TRIGGERS):
        return ParsedVoiceCommand(raw_phrase=phrase, normalized_phrase=normalized, wake_word_detected=wake, module_key="killerkoala_banter", target=target, owned_device=owned, raw_addresses=raw_addresses)
    return ParsedVoiceCommand(phrase, normalized, wake, "killerkoala_help")


def _failure_result(parsed: ParsedVoiceCommand, reason: str, xp_state: KillerKoalaXPState, started: float) -> VoiceExecutionResult:
