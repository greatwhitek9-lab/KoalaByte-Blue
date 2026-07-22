#!/usr/bin/env python3
"""Validate the Pi-side KillerKoala AI, STT, expression, and TTS contract.

This gate is offline and hardware-free. It executes actual routing behavior,
including the confirmed ESP32 wake-session follow-up used by complex voice input.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import queue
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
STATUS_PATH = ROOT / "logs" / "killerkoala" / "killerkoala_ai_readiness.json"
VENV_BIN = PI_ROOT / ".venv" / "bin"

for path in (ROOT, PI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

REQUIRED_FILES = (
    "pi-companion/requirements.txt",
    "pi-companion/koalablue/killerkoala_vocabulary.py",
    "pi-companion/koalablue/killerkoala_expression.py",
    "pi-companion/koalablue/killerkoala_web_research.py",
    "pi-companion/koalablue/killerkoala_hybrid_companion.py",
    "pi-companion/koalablue/killerkoala_voice_control.py",
    "pi-companion/koalablue/dualeye_tts.py",
    "pi-companion/koalablue/esp32_dualeye_speech_synced_bridge.py",
    "pi-companion/koalablue/esp32_dualeye_error_dig_bridge.py",
    "scripts/check_confirmed_wake_audio.py",
    "scripts/setup_killerkoala_ollama.sh",
    "scripts/install_esp32_dualeye_voice_bridge_service.sh",
    "training/killerkoala_lora/Modelfile.killerkoala-tinyllama",
    "firmware/esp32-dualeye/scripts/patch_tinyllama_vocabulary_fallback.py",
    "firmware/esp32-dualeye/scripts/patch_tone_expression_payloads.py",
    "firmware/esp32-dualeye/scripts/patch_local_speech_lifecycle.py",
    "firmware/t114-combined-safe/scripts/generate_tone_aware_main.py",
)

REQUIRED_IMPORTS = (
    "httpx",
    "serial",
    "speech_recognition",
    "pocketsphinx",
    "koalablue.killerkoala_expression",
    "koalablue.killerkoala_web_research",
    "koalablue.killerkoala_hybrid_companion",
    "koalablue.killerkoala_voice_control",
    "koalablue.dualeye_tts",
    "koalablue.esp32_dualeye_error_dig_bridge",
)

OPTIONAL_IMPORTS = ("requests", "pyttsx3")

REQUIRED_REQUIREMENTS = (
    "httpx",
    "requests",
    "pyserial",
    "pyttsx3",
    "SpeechRecognition",
    "pocketsphinx",
    "edge-tts",
)


def command_path(command: str) -> str | None:
    found = shutil.which(command)
    if found:
        return found
    candidate = VENV_BIN / command
    return str(candidate) if candidate.exists() else None


def import_modules(
    names: tuple[str, ...],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    status: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for module in names:
        try:
            imported = importlib.import_module(module)
            version = getattr(imported, "__version__", None)
            status[module] = {
                "available": True,
                "version": str(version) if version else None,
            }
        except Exception as exc:
            status[module] = {"available": False, "error": str(exc)}
            failures.append(f"runtime import failed: {module} ({exc})")
    return status, failures


def requirement_failures() -> list[str]:
    text = (PI_ROOT / "requirements.txt").read_text(
        encoding="utf-8", errors="ignore"
    ).lower()
    return [
        f"pi-companion/requirements.txt missing voice/AI dependency: {requirement}"
        for requirement in REQUIRED_REQUIREMENTS
        if requirement.lower() not in text
    ]


def essential_file_contract_failures() -> list[str]:
    failures: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).exists():
            failures.append(f"missing current KillerKoala runtime file: {relative}")

    tts = (PI_ROOT / "koalablue" / "dualeye_tts.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    if 'WILLIAM_VOICE = "en-AU-WilliamNeural"' not in tts:
        failures.append("Australian male William TTS constant is missing")
    if 'SPOKEN_IDENTITY = "KillerKoala"' not in tts:
        failures.append("KillerKoala spoken identity constant is missing")

    modelfile = (
        ROOT / "training/killerkoala_lora/Modelfile.killerkoala-tinyllama"
    ).read_text(encoding="utf-8", errors="ignore")
    if "FROM tinyllama:1.1b" not in modelfile:
        failures.append(
            "KillerKoala Modelfile no longer derives from tinyllama:1.1b"
        )
    return failures


def confirmed_wake_audio_smoke() -> dict[str, Any]:
    from koalablue.esp32_dualeye_error_dig_bridge import (
        ESP32DualEyeVoiceBridge,
    )

    bridge = object.__new__(ESP32DualEyeVoiceBridge)
    request_id = "confirmed-wake-smoke"
    bridge._audio = {request_id: bytearray(b"\x00\x00" * 320)}
    bridge._audio_meta = {
        request_id: {
            "sample_rate": 16000,
            "sample_width": 2,
            "wake_already_confirmed": True,
            "phrase_prefix": "killerkoala",
            "capture_purpose": "complex_ai",
            "menu_was_visible": False,
        }
    }
    bridge.events = queue.Queue()
    writes: list[dict[str, Any]] = []
    bridge._transcribe_pcm = (  # type: ignore[method-assign]
        lambda _pcm, _sample_rate, _sample_width: "what is the current system status"
    )
    bridge._write_json = (  # type: ignore[method-assign]
        lambda payload, **_kwargs: writes.append(dict(payload))
    )
    bridge._fanout_face = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    bridge._log_event = lambda _event: None  # type: ignore[method-assign]

    event = ESP32DualEyeVoiceBridge._finish_audio(
        bridge,
        {
            "request_id": request_id,
            "wake_already_confirmed": True,
            "capture_purpose": "complex_ai",
        },
    )
    return {
        "event_created": event is not None,
        "routed_phrase": event.phrase if event is not None else "",
        "original_transcript": (
            event.payload.get("transcript") if event is not None else ""
        ),
        "wake_word_injected_for_routing": bool(
            event
            and event.payload.get("wake_word_injected_for_routing")
        ),
        "rejected": any(
            payload.get("type") == "voice_rejected" for payload in writes
        ),
    }


def safe_smoke() -> dict[str, Any]:
    previous = {
        name: os.environ.get(name)
        for name in (
            "KILLERKOALA_LLM_MODE",
            "KILLERKOALA_WEB_SEARCH",
            "KILLERKOALA_DIALOGUE_TURNS",
        )
    }
    os.environ["KILLERKOALA_LLM_MODE"] = "off"
    os.environ["KILLERKOALA_WEB_SEARCH"] = "off"
    os.environ["KILLERKOALA_DIALOGUE_TURNS"] = "0"
    try:
        from koalablue.dualeye_tts import (
            SPOKEN_IDENTITY,
            WILLIAM_VOICE,
            sanitize_spoken_identity,
        )
        from koalablue.esp32_dualeye_error_dig_bridge import (
            ESP32DualEyeVoiceBridge,
        )
        from koalablue.killerkoala_expression import classify_response_expression
        from koalablue.killerkoala_hybrid_companion import (
            companion_response,
            load_config,
        )
        from koalablue.killerkoala_voice_control import (
            module_manifest,
            parse_voice_command,
        )
        from koalablue.killerkoala_web_research import (
            looks_like_general_question,
            question_needs_web,
        )

        manifest = module_manifest()
        help_parsed = parse_voice_command(
            "killerkoala voice commands", require_wake_word=True
        )
        question_parsed = parse_voice_command(
            "killerkoala what is the current Raspberry Pi operating system release",
            require_wake_word=True,
        )
        response = companion_response(
            "status",
            xp=100,
            user_text="Pi readiness check",
            history_path=None,
        )
        happy = classify_response_expression(
            "Bonza, the action completed successfully.", status="success"
        )
        angry = classify_response_expression(
            "The system fault is unacceptable and blocked.", status="error"
        )
        curious = classify_response_expression(
            "What is the latest firmware release?", event="question"
        )
        config = load_config()
        return {
            "wake_word": manifest.get("wake_word"),
            "help_module_present": "killerkoala_help"
            in manifest.get("modules", {}),
            "question_module_present": "killerkoala_question"
            in manifest.get("modules", {}),
            "help_module_key": help_parsed.module_key,
            "question_module_key": question_parsed.module_key,
            "question_detector": looks_like_general_question(
                "what is the latest firmware?"
            ),
            "web_disabled_for_smoke": not question_needs_web(
                "what is the latest firmware?"
            ),
            "companion_source": response.source,
            "companion_text": response.text,
            "default_model": config.model,
            "william_voice_backend": WILLIAM_VOICE,
            "spoken_identity": SPOKEN_IDENTITY,
            "sanitized_identity_sample": sanitize_spoken_identity(
                "G'day, I am William."
            ),
            "production_bridge_class": ESP32DualEyeVoiceBridge.__name__,
            "confirmed_wake_audio": confirmed_wake_audio_smoke(),
            "happy_expression": happy.to_payload(),
            "angry_expression": angry.to_payload(),
            "curious_expression": curious.to_payload(),
        }
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check KillerKoala TinyLlama, offline STT, expression, and William "
            "TTS readiness"
        )
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Promote optional host integrations to required checks",
    )
    parser.add_argument("--status-path", default=str(STATUS_PATH))
    args = parser.parse_args()

    failures = requirement_failures() + essential_file_contract_failures()
    warnings: list[str] = []

    required_imports, required_failures = import_modules(REQUIRED_IMPORTS)
    failures.extend(required_failures)
    optional_imports, optional_failures = import_modules(OPTIONAL_IMPORTS)
    if args.strict:
        failures.extend(optional_failures)
    else:
        warnings.extend(optional_failures)

    edge_tts = command_path("edge-tts")
    ffmpeg = command_path("ffmpeg")
    espeak = command_path("espeak-ng") or command_path("espeak")
    for label, value in (
        ("edge-tts", edge_tts),
        ("ffmpeg", ffmpeg),
        ("espeak fallback", espeak),
    ):
        if not value:
            message = f"local TTS host command unavailable: {label}"
            (failures if args.strict else warnings).append(message)

    try:
        smoke = safe_smoke()
        confirmed = smoke.get("confirmed_wake_audio", {})
        checks = (
            (
                smoke.get("wake_word") == "killerkoala",
                "voice manifest wake word is not killerkoala",
            ),
            (
                smoke.get("help_module_present")
                and smoke.get("help_module_key") == "killerkoala_help",
                "help phrase did not route to killerkoala_help",
            ),
            (
                smoke.get("question_module_present")
                and smoke.get("question_module_key") == "killerkoala_question",
                "open-ended question did not route to killerkoala_question",
            ),
            (
                bool(smoke.get("question_detector")),
                "general-question detector rejected a factual question",
            ),
            (
                bool(smoke.get("web_disabled_for_smoke")),
                "offline smoke test unexpectedly requested web access",
            ),
            (
                smoke.get("default_model") == "killerkoala-tinyllama:latest",
                "default Pi model is not killerkoala-tinyllama:latest",
            ),
            (
                smoke.get("william_voice_backend") == "en-AU-WilliamNeural",
                "William Neural is not the Australian male TTS backend",
            ),
            (
                smoke.get("spoken_identity") == "KillerKoala",
                "spoken identity is not KillerKoala",
            ),
            (
                "William"
                not in str(smoke.get("sanitized_identity_sample", "")),
                "William backend name leaked through identity sanitization",
            ),
            (
                "William" not in str(smoke.get("companion_text", "")),
                "companion response exposed the William backend name",
            ),
            (
                bool(confirmed.get("event_created")),
                "confirmed wake-session follow-up did not create a voice event",
            ),
            (
                confirmed.get("routed_phrase")
                == "killerkoala what is the current system status",
                "confirmed wake-session follow-up was not prefixed for routing",
            ),
            (
                confirmed.get("original_transcript")
                == "what is the current system status",
                "confirmed wake-session original transcript was not preserved",
            ),
            (
                bool(confirmed.get("wake_word_injected_for_routing")),
                "confirmed wake-session routing did not record prefix injection",
            ),
            (
                not bool(confirmed.get("rejected")),
                "confirmed wake-session follow-up was incorrectly rejected",
            ),
            (
                smoke.get("happy_expression", {}).get("tone")
                in {"happy", "excited"},
                "happy response did not select a happy display expression",
            ),
            (
                smoke.get("angry_expression", {}).get("tone")
                in {"angry", "error"},
                "angry response did not select an angry display expression",
            ),
            (
                smoke.get("curious_expression", {}).get("tone") == "curious",
                "question did not select a curious display expression",
            ),
        )
        failures.extend(message for passed, message in checks if not passed)
    except Exception as exc:
        smoke = {"status": "error", "error": str(exc)}
        failures.append(f"KillerKoala behavioral smoke check failed: {exc}")

    payload = {
        "status": (
            "KILLERKOALA_AI_READY"
            if not failures
            else "KILLERKOALA_AI_INCOMPLETE"
        ),
        "runtime_mode": "headless_pi_os_lite",
        "response_hierarchy": [
            "waveshare_saved_vocabulary_and_basic_responses",
            "raspberry_pi_tinyllama_for_unmatched_or_open_ended_requests",
            "web_research_context_when_internet_is_available",
            "local_phrase_fallback_if_tinyllama_is_unavailable",
        ],
        "primary_pi_model": "killerkoala-tinyllama:latest",
        "offline_stt_backend": "pocketsphinx",
        "confirmed_wake_followup": True,
        "spoken_identity": "KillerKoala",
        "tts_backend": "en-AU-WilliamNeural",
        "tone_synced_displays": True,
        "network_request_performed": False,
        "microphone_hardware_required_for_check": False,
        "audio_playback_performed": False,
        "firmware_flash_performed": False,
        "required_imports": required_imports,
        "optional_imports": optional_imports,
        "tts_commands": {
            "edge_tts": edge_tts,
            "ffmpeg": ffmpeg,
            "espeak": espeak,
        },
        "smoke": smoke,
        "warnings": warnings,
        "failures": failures,
        "updated_at": time.time(),
    }
    out = Path(args.status_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "status_path": str(out),
                "warnings": warnings,
                "failures": failures,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
