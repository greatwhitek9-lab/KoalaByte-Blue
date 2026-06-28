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
    return "raw address" in phrase or "raw addresses" in phrase or "raw mac" in phrase


def _flexible_banter_requested(phrase: str, force_flexible: bool = False) -> bool:
    if force_flexible:
        return True
    return any(token in phrase for token in FLEXIBLE_BANTER_TRIGGERS)


def parse_voice_command(phrase: str, require_wake_word: bool = True) -> ParsedVoiceCommand:
    normalized = _normalize_phrase(phrase)
    wake_detected = WAKE_WORD in normalized
    working = normalized.replace(WAKE_WORD, " ").strip() if wake_detected else normalized

    if require_wake_word and not wake_detected:
        return ParsedVoiceCommand(phrase, normalized, False, None, _extract_target(normalized), _owned_device_ack(normalized), _raw_addresses_ack(normalized))

    module_key: Optional[str] = None
    for key, spec in VOICE_MODULES.items():
        if any(_normalize_phrase(alias) in working for alias in spec.phrases):
            module_key = key
            break

    menu_action = None
    if module_key is None:
        menu_action = _resolve_menu_action(working)
        if menu_action is not None:
            module_key = f"menu:{menu_action.command}"

    return ParsedVoiceCommand(phrase, normalized, wake_detected, module_key, _extract_target(normalized), _owned_device_ack(normalized), _raw_addresses_ack(normalized), menu_action=menu_action)


def _artifacts_from_payload(payload: Any) -> Dict[str, str]:
    data = _jsonable(payload)
    artifacts: Dict[str, str] = {}
    if isinstance(data, dict):
        nested_artifacts = data.get("artifacts", {})
        if isinstance(nested_artifacts, dict):
            for key, value in nested_artifacts.items():
                artifacts[str(key)] = str(value)
        for key in ("artifact_path", "manifest_path", "jsonl_path", "csv_path", "summary_path", "plan_path", "output_jsonl_path", "wigle_csv_path", "geojson_path"):
            if data.get(key):
                artifacts[key] = str(data[key])
    return artifacts


def _companion(event: str, xp: int, parsed: ParsedVoiceCommand, context: Optional[Dict[str, Any]] = None, force_flexible: bool = False) -> Any:
    return companion_response(
        event,
        xp=xp,
        user_text=parsed.raw_phrase,
        context=context or {},
        flexible=_flexible_banter_requested(parsed.normalized_phrase, force_flexible=force_flexible),
        history_path=Path("logs/killerkoala/killerkoala_phrase_history.json"),
    )


def _blocked_result(parsed: ParsedVoiceCommand, reason: str, xp: KillerKoalaXPState, output_dir: Path, xp_path: Path, force_flexible: bool = False) -> VoiceExecutionResult:
    now = time.time()
    xp.failed_modules += 1
    save_xp_state(xp, xp_path)
    companion = _companion("error", xp.xp, parsed, {"status": "blocked", "error": reason}, force_flexible=force_flexible)
    result = VoiceExecutionResult(
        status="blocked",
        module_key=parsed.module_key,
        module_title=VOICE_MODULES.get(parsed.module_key).title if parsed.module_key in VOICE_MODULES else None,
        phrase=parsed.raw_phrase,
        started_at=now,
        ended_at=now,
        xp_before=xp.xp,
        xp_after=xp.xp,
        xp_reward=0,
        rank_before=rank_for_xp(xp.xp),
        rank_after=rank_for_xp(xp.xp),
        companion_line=companion.text,
        safety={"blocked": True, "reason": reason, "companion_source": companion.source, "llm_used": companion.llm_used},
        details={"companion": asdict(companion)},
        error=reason,
    )
    out = output_dir / f"killerkoala_voice_blocked_{int(now)}.json"
    result.artifacts["voice_result"] = str(out)
    _write_json(out, asdict(result))
    return result


def _spec_for_parsed(parsed: ParsedVoiceCommand) -> Optional[VoiceModuleSpec]:
    if parsed.module_key in VOICE_MODULES:
        return VOICE_MODULES[parsed.module_key]
    if parsed.menu_action is not None:
        return VoiceModuleSpec(parsed.module_key or "menu", f"Menu Action: {parsed.menu_action.label}", parsed.menu_action.aliases[:12], 3, "menu_action", "Run an enabled menu item through the same automated select path used by the UI.")
    return None


def _run_menu_payload(parsed: ParsedVoiceCommand) -> dict[str, Any]:
    from .menu_action_runner import run_automated_menu_action

    if parsed.menu_action is not None:
        return run_automated_menu_action(parsed.menu_action.command, parsed.menu_action.label, parsed.menu_action.group)
    command, label, group = BASE_MODULE_TO_MENU_COMMAND.get(parsed.module_key or "", ("", "", ""))
    if not command:
        raise ValueError(f"unsupported voice module: {parsed.module_key}")
    return run_automated_menu_action(command, label, group)


def _payload_success(payload: Any) -> bool:
    data = _jsonable(payload)
    status = str(data.get("status", "") if isinstance(data, dict) else "").upper()
    return not any(token in status for token in ("ERROR", "FAILED", "SKIPPED", "BLOCKED"))


def execute_module(parsed: ParsedVoiceCommand, output_dir: Path = DEFAULT_OUTPUT_DIR, xp_path: Path = DEFAULT_XP_PATH, force_flexible_banter: bool = False) -> VoiceExecutionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    xp_state = load_xp_state(xp_path)
    xp_before = xp_state.xp
    rank_before = rank_for_xp(xp_before)
    started = time.time()

    if not parsed.wake_word_detected:
        return _blocked_result(parsed, "wake word 'killerkoala' was not detected", xp_state, output_dir, xp_path, force_flexible_banter)

    spec = _spec_for_parsed(parsed)
    if parsed.module_key is None or spec is None:
        return _blocked_result(parsed, "no supported module or menu action phrase was detected", xp_state, output_dir, xp_path, force_flexible_banter)

    if parsed.module_key in VOICE_MODULES:
        if spec.target_required and not parsed.target:
            return _blocked_result(parsed, f"{spec.title} requires a target Bluetooth address", xp_state, output_dir, xp_path, force_flexible_banter)
        if spec.owned_device_required and not parsed.owned_device:
            return _blocked_result(parsed, f"{spec.title} requires the phrase 'owned device' or 'in scope'", xp_state, output_dir, xp_path, force_flexible_banter)

    details: Dict[str, Any] = {}
    artifacts: Dict[str, str] = {}
    status_value = "success"
    error: Optional[str] = None

    try:
        if parsed.module_key == "killerkoala_help":
            manifest_path = output_dir / "killerkoala_voice_modules.json"
            _write_json(manifest_path, module_manifest())
            payload = {"action": "killerkoala Help", "manifest_path": str(manifest_path)}
        else:
            payload = _run_menu_payload(parsed)
            if not _payload_success(payload):
                status_value = "blocked"
        details = _jsonable(payload)
        artifacts = _artifacts_from_payload(payload)
    except Exception as exc:
        status_value = "error"
        error = str(exc)

    ended = time.time()
    xp_reward = spec.xp_reward if status_value == "success" else 0
    if status_value == "success":
        xp_state.xp += xp_reward
        xp_state.successful_modules += 1
        xp_state.last_module = spec.title
    else:
        xp_state.failed_modules += 1
    save_xp_state(xp_state, xp_path)

    rank_after = rank_for_xp(xp_state.xp)
    event = "level_up" if rank_after != rank_before else spec.event
    companion = _companion(event, xp_state.xp, parsed, {"module": parsed.module_key, "module_title": spec.title, "status": status_value, "error": error, "xp_reward": xp_reward}, force_flexible=force_flexible_banter)

    result = VoiceExecutionResult(
        status=status_value,
        module_key=parsed.module_key,
        module_title=spec.title,
        phrase=parsed.raw_phrase,
        started_at=started,
        ended_at=ended,
        xp_before=xp_before,
        xp_after=xp_state.xp,
        xp_reward=xp_reward,
        rank_before=rank_before,
        rank_after=rank_after,
        companion_line=companion.text,
        artifacts=artifacts,
        safety={
            "authorized_lab_use_only": True,
            "raw_addresses_requested": parsed.raw_addresses,
            "owned_device_confirmed": parsed.owned_device,
            "target": parsed.target,
            "restricted_placeholder_enabled": False,
            "xp_awarded_on_success_only": True,
            "manual_prompt_required": False,
            "voice_menu_action": parsed.menu_action is not None,
            "companion_source": companion.source,
            "llm_requested": companion.llm_requested,
            "llm_used": companion.llm_used,
            "llm_model": companion.llm_model,
            "llm_fallback_reason": companion.fallback_reason,
        },
        details={"module_result": details, "companion": asdict(companion)},
        error=error,
    )

    out = output_dir / f"killerkoala_voice_result_{int(started)}.json"
    result.artifacts["voice_result"] = str(out)
    _write_json(out, asdict(result))
    return result


def speak(text: str) -> bool:
    try:
        import pyttsx3  # type: ignore
    except Exception:
        return False
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return True


def listen_once(timeout: int = 5, phrase_time_limit: int = 8) -> str:
    try:
        import speech_recognition as sr  # type: ignore
    except Exception as exc:
        raise RuntimeError("microphone mode requires SpeechRecognition and PyAudio installed on the Pi") from exc
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:  # type: ignore[attr-defined]
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    return str(recognizer.recognize_google(audio))


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="killerkoala spoken-command module and menu-action executor")
    parser.add_argument("--phrase", default=None, help="Typed spoken phrase for CI/testing, e.g. 'killerkoala run Wi-Fi + BLE Survey'")
    parser.add_argument("--listen", action="store_true", help="Listen once from the microphone using optional SpeechRecognition/PyAudio")
    parser.add_argument("--loop", action="store_true", help="Continuously listen for commands until interrupted")
    parser.add_argument("--no-wake-required", action="store_true", help="Testing mode: do not require the killerkoala wake word")
    parser.add_argument("--flexible-banter", action="store_true", help="Allow optional tiny LLM/Ollama LoRA banter path for this response")
    parser.add_argument("--speak", action="store_true", help="Speak the response if optional pyttsx3 is installed")
    parser.add_argument("--manifest", action="store_true", help="Write and print supported module/menu-action manifest")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    xp_path = Path(args.xp_path)

    if args.manifest:
        out = output_dir / "killerkoala_voice_modules.json"
        _write_json(out, module_manifest())
        print(json.dumps({"manifest_path": str(out), "modules": sorted(VOICE_MODULES), "menu_action_count": len(voice_menu_actions())}, indent=2, sort_keys=True))
        return 0

    def handle_phrase(phrase: str) -> VoiceExecutionResult:
        parsed = parse_voice_command(phrase, require_wake_word=not args.no_wake_required)
        result = execute_module(parsed, output_dir=output_dir, xp_path=xp_path, force_flexible_banter=args.flexible_banter)
        print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
        if args.speak:
            speak(result.companion_line)
        return result

    if args.phrase:
        handle_phrase(args.phrase)
        return 0

    if args.listen or args.loop:
        while True:
            phrase = listen_once()
            handle_phrase(phrase)
            if not args.loop:
                break
        return 0

    parser.error("provide --phrase, --listen, --loop, or --manifest")
    return 2


if __name__ == "__main__":
    raise SystemExit(run_cli())
