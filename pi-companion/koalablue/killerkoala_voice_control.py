from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .killerkoala_vocabulary import line_for_event, rank_for_xp


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
    "bluez_status": VoiceModuleSpec("bluez_status", "Eucalyptus Bus Scout", ["eucalyptus bus scout", "bluez status", "adapter status", "controller status", "check bluetooth status"], 5, "bluez_status", "Collect local Bluetooth controller and adapter status."),
    "bluez_scan": VoiceModuleSpec("bluez_scan", "Dropbear Discovery Sweep", ["dropbear discovery sweep", "bluez scan", "bluetooth scan", "discovery sweep", "scan bluetooth"], 10, "scan_complete", "Run bounded local Bluetooth discovery. Addresses are hashed unless raw logging is explicitly requested."),
    "bluez_monitor": VoiceModuleSpec("bluez_monitor", "Billabong HCI Watch", ["billabong hci watch", "bluez monitor", "hci monitor", "btmon", "monitor bluetooth"], 8, "bluez_status", "Run bounded local btmon capture for owned lab debugging."),
    "bluez_all_safe": VoiceModuleSpec("bluez_all_safe", "Kookaburra Safe Nest Run", ["kookaburra safe nest run", "safe nest run", "run all safe", "bluez all safe"], 12, "bluez_status", "Run BlueZ inventory, status, and bounded discovery with safe defaults."),
    "bluez_info": VoiceModuleSpec("bluez_info", "Joey Target Card", ["joey target card", "bluez info", "target card", "device info"], 5, "bluez_status", "Show target info only for an owned or written-scope device.", owned_device_required=True, target_required=True),
    "bluez_services": VoiceModuleSpec("bluez_services", "Treehouse Service Notes", ["treehouse service notes", "service notes", "browse services", "bluez services"], 5, "bluez_status", "Browse service notes only for an owned or written-scope device.", owned_device_required=True, target_required=True),
    "gatt_readiness": VoiceModuleSpec("gatt_readiness", "Gumnut GATT Readiness", ["gumnut gatt readiness", "gatt readiness", "gatt checklist", "owned gatt checklist"], 4, "bluez_status", "Write an owned-device GATT readiness checklist. Does not perform GATT writes.", owned_device_required=True, target_required=True),
    "koala_kapture": VoiceModuleSpec("koala_kapture", "Koala Kapture", ["koala kapture", "kapture", "capture ble", "capture metadata", "metadata capture"], 15, "capture_saved", "Run passive BLE metadata capture only."),
    "koala_kry": VoiceModuleSpec("koala_kry", "Koala Kry", ["koala kry", "kry", "offline replay", "replay metadata"], 5, "koala_kry", "Replay captured metadata offline only. No RF transmission."),
    "ear_tag_tx_lab": VoiceModuleSpec("ear_tag_tx_lab", "KoalaByte Lab", ["koalabyte lab", "koala byte lab", "ear tag tx lab", "ear tag", "lab beacon plan", "beacon plan"], 5, "ear_tag_tx_lab", "Write a synthetic owned-device BLE advertisement plan artifact."),
    "killerkoala_help": VoiceModuleSpec("killerkoala_help", "killerkoala Help", ["help", "what can you do", "list commands", "voice commands"], 1, "inquiry_help", "Show available voice-controlled modules."),
}


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


def module_manifest() -> Dict[str, Any]:
    return {
        "wake_word": WAKE_WORD,
        "modules": {key: asdict(spec) for key, spec in sorted(VOICE_MODULES.items())},
        "safety": {
            "authorized_lab_use_only": True,
            "restricted_placeholder_enabled": False,
            "xp_awarded_on_success_only": True,
            "target_specific_modules_require_owned_device_phrase": True,
            "voice_activation_can_be_tested_with_typed_phrases": True,
        },
    }


def _normalize_phrase(phrase: str) -> str:
    return re.sub(r"\s+", " ", phrase.strip().lower())


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


def parse_voice_command(phrase: str, require_wake_word: bool = True) -> ParsedVoiceCommand:
    normalized = _normalize_phrase(phrase)
    wake_detected = WAKE_WORD in normalized
    working = normalized.replace(WAKE_WORD, " ").strip() if wake_detected else normalized

    if require_wake_word and not wake_detected:
        return ParsedVoiceCommand(phrase, normalized, False, None, _extract_target(normalized), _owned_device_ack(normalized), _raw_addresses_ack(normalized))

    module_key: Optional[str] = None
    for key, spec in VOICE_MODULES.items():
        if any(alias in working for alias in spec.phrases):
            module_key = key
            break

    return ParsedVoiceCommand(phrase, normalized, wake_detected, module_key, _extract_target(normalized), _owned_device_ack(normalized), _raw_addresses_ack(normalized))


def _artifacts_from_payload(payload: Any) -> Dict[str, str]:
    data = _jsonable(payload)
    artifacts: Dict[str, str] = {}
    if isinstance(data, dict):
        nested_artifacts = data.get("artifacts", {})
        if isinstance(nested_artifacts, dict):
            for key, value in nested_artifacts.items():
                artifacts[str(key)] = str(value)
        for key in ("manifest_path", "jsonl_path", "csv_path", "summary_path", "plan_path", "output_jsonl_path"):
            if data.get(key):
                artifacts[key] = str(data[key])
    return artifacts


def _blocked_result(parsed: ParsedVoiceCommand, reason: str, xp: KillerKoalaXPState, output_dir: Path, xp_path: Path) -> VoiceExecutionResult:
    now = time.time()
    xp.failed_modules += 1
    save_xp_state(xp, xp_path)
    line = line_for_event("error", xp=xp.xp).selected_text
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
        companion_line=line,
        safety={"blocked": True, "reason": reason},
        error=reason,
    )
    out = output_dir / f"killerkoala_voice_blocked_{int(now)}.json"
    result.artifacts["voice_result"] = str(out)
    _write_json(out, asdict(result))
    return result


def execute_module(parsed: ParsedVoiceCommand, output_dir: Path = DEFAULT_OUTPUT_DIR, xp_path: Path = DEFAULT_XP_PATH) -> VoiceExecutionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    xp_state = load_xp_state(xp_path)
    xp_before = xp_state.xp
    rank_before = rank_for_xp(xp_before)
    started = time.time()

    if not parsed.wake_word_detected:
        return _blocked_result(parsed, "wake word 'killerkoala' was not detected", xp_state, output_dir, xp_path)
    if parsed.module_key is None or parsed.module_key not in VOICE_MODULES:
        return _blocked_result(parsed, "no supported module phrase was detected", xp_state, output_dir, xp_path)

    spec = VOICE_MODULES[parsed.module_key]
    if spec.target_required and not parsed.target:
        return _blocked_result(parsed, f"{spec.title} requires a target Bluetooth address", xp_state, output_dir, xp_path)
    if spec.owned_device_required and not parsed.owned_device:
        return _blocked_result(parsed, f"{spec.title} requires the phrase 'owned device' or 'in scope'", xp_state, output_dir, xp_path)

    details: Dict[str, Any] = {}
    artifacts: Dict[str, str] = {}
    status_value = "success"
    error: Optional[str] = None

    try:
        if parsed.module_key == "bluez_manifest":
            from .bluez_tools import module_manifest as bluez_module_manifest

            payload = bluez_module_manifest(output_dir / "bluez")
        elif parsed.module_key == "bluez_inventory":
            from .bluez_tools import inventory

            payload = inventory(output_dir / "bluez")
        elif parsed.module_key == "bluez_status":
            from .bluez_tools import status as bluez_status

            payload = bluez_status(output_dir / "bluez", raw_addresses=parsed.raw_addresses)
        elif parsed.module_key == "bluez_scan":
            from .bluez_tools import scan

            duration = _extract_duration(parsed.normalized_phrase, 15, 3, 120)
            parsed.duration_seconds = duration
            payload = scan(duration, output_dir / "bluez", raw_addresses=parsed.raw_addresses)
        elif parsed.module_key == "bluez_monitor":
            from .bluez_tools import monitor

            duration = _extract_duration(parsed.normalized_phrase, 20, 5, 300)
            parsed.duration_seconds = duration
            payload = monitor(duration, output_dir / "bluez")
        elif parsed.module_key == "bluez_all_safe":
            from .bluez_tools import all_safe

            duration = _extract_duration(parsed.normalized_phrase, 15, 3, 120)
            parsed.duration_seconds = duration
            payload = all_safe(duration, output_dir / "bluez", raw_addresses=parsed.raw_addresses)
        elif parsed.module_key == "bluez_info":
            from .bluez_tools import info

            payload = info(parsed.target or "", parsed.owned_device, output_dir / "bluez", raw_addresses=parsed.raw_addresses)
        elif parsed.module_key == "bluez_services":
            from .bluez_tools import services

            payload = services(parsed.target or "", parsed.owned_device, output_dir / "bluez", raw_addresses=parsed.raw_addresses)
        elif parsed.module_key == "gatt_readiness":
            from .bluez_tools import gatt_readiness

            payload = gatt_readiness(parsed.target or "", parsed.owned_device, output_dir / "bluez")
        elif parsed.module_key == "koala_kapture":
            from .koala_kapture import KoalaKaptureConfig, KoalaKaptureRecorder

            duration = _extract_duration(parsed.normalized_phrase, 15, 3, 120)
            parsed.duration_seconds = duration
            config = KoalaKaptureConfig(output_dir=str(output_dir / "koala_kapture"), duration_seconds=float(duration), max_records=1000)
            payload = asyncio.run(KoalaKaptureRecorder(config).record())
        elif parsed.module_key == "koala_kry":
            from .koala_kry import KoalaKryConfig, KoalaKryReplay

            payload = KoalaKryReplay(KoalaKryConfig(input_dir=str(output_dir / "koala_kapture"), output_dir=str(output_dir / "koala_kry_replay"))).replay()
        elif parsed.module_key == "ear_tag_tx_lab":
            from .ear_tag_tx_lab import write_ear_tag_tx_lab_plan

            plan_path = write_ear_tag_tx_lab_plan(output_dir / "koalabyte_lab")
            payload = {"action": "KoalaByte Lab", "plan_path": str(plan_path)}
        elif parsed.module_key == "killerkoala_help":
            manifest_path = output_dir / "killerkoala_voice_modules.json"
            _write_json(manifest_path, module_manifest())
            payload = {"action": "killerkoala Help", "manifest_path": str(manifest_path)}
        else:
            raise ValueError(f"unsupported module key: {parsed.module_key}")

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
    companion_line = line_for_event(event, xp=xp_state.xp).selected_text

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
        companion_line=companion_line,
        artifacts=artifacts,
        safety={
            "authorized_lab_use_only": True,
            "raw_addresses_requested": parsed.raw_addresses,
            "owned_device_confirmed": parsed.owned_device,
            "target": parsed.target,
            "restricted_placeholder_enabled": False,
            "xp_awarded_on_success_only": True,
        },
        details=details,
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
    parser = argparse.ArgumentParser(description="killerkoala spoken-command module executor")
    parser.add_argument("--phrase", default=None, help="Typed spoken phrase for CI/testing, e.g. 'killerkoala run bluez inventory'")
    parser.add_argument("--listen", action="store_true", help="Listen once from the microphone using optional SpeechRecognition/PyAudio")
    parser.add_argument("--loop", action="store_true", help="Continuously listen for commands until interrupted")
    parser.add_argument("--no-wake-required", action="store_true", help="Testing mode: do not require the killerkoala wake word")
    parser.add_argument("--speak", action="store_true", help="Speak the response if optional pyttsx3 is installed")
    parser.add_argument("--manifest", action="store_true", help="Write and print supported module manifest")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    xp_path = Path(args.xp_path)

    if args.manifest:
        out = output_dir / "killerkoala_voice_modules.json"
        _write_json(out, module_manifest())
        print(json.dumps({"manifest_path": str(out), "modules": sorted(VOICE_MODULES)}, indent=2, sort_keys=True))
        return 0

    def handle_phrase(phrase: str) -> VoiceExecutionResult:
        parsed = parse_voice_command(phrase, require_wake_word=not args.no_wake_required)
        result = execute_module(parsed, output_dir=output_dir, xp_path=xp_path)
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
