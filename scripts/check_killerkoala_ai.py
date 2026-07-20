#!/usr/bin/env python3
"""Validate the current Pi-side KillerKoala AI, voice, web, and TTS contract.

Firmware compilation remains owned by the dedicated ESP32/T114 workflows. This
Pi gate performs no network request, microphone capture, firmware flash, or audio
playback. It verifies local-vocabulary-first routing, TinyLlama question fallback,
web-research controls, Australian TTS identity, and tone-expression metadata.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
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
    "pi-companion/koalablue/esp32_dualeye_voice_bridge.py",
    "pi-companion/koalablue/esp32_dualeye_latched_koalagotchi_bridge.py",
    "pi-companion/koalablue/esp32_dualeye_speech_synced_bridge.py",
    "scripts/run_killerkoala_hybrid.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_esp32_dualeye_voice_bridge.py",
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
    "requests",
    "serial",
    "pyttsx3",
    "speech_recognition",
    "koalablue.killerkoala_vocabulary",
    "koalablue.killerkoala_expression",
    "koalablue.killerkoala_web_research",
    "koalablue.killerkoala_hybrid_companion",
    "koalablue.killerkoala_voice_control",
    "koalablue.dualeye_tts",
    "koalablue.esp32_dualeye_speech_synced_bridge",
)

REQUIRED_REQUIREMENTS = (
    "httpx",
    "requests",
    "pyserial",
    "pyttsx3",
    "SpeechRecognition",
    "edge-tts",
)


def command_path(command: str) -> str | None:
    found = shutil.which(command)
    if found:
        return found
    candidate = VENV_BIN / command
    return str(candidate) if candidate.exists() else None


def missing_files() -> list[str]:
    return [relative for relative in REQUIRED_FILES if not (ROOT / relative).exists()]


def import_status() -> tuple[dict[str, dict[str, Any]], list[str]]:
    status: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for module in REQUIRED_IMPORTS:
        try:
            imported = importlib.import_module(module)
            version = getattr(imported, "__version__", None)
            status[module] = {"available": True, "version": str(version) if version else None}
        except Exception as exc:
            status[module] = {"available": False, "error": str(exc)}
            failures.append(f"KillerKoala runtime import failed: {module} ({exc})")
    return status, failures


def requirement_failures() -> list[str]:
    text = (PI_ROOT / "requirements.txt").read_text(encoding="utf-8", errors="ignore").lower()
    return [
        f"pi-companion/requirements.txt missing voice/AI dependency: {requirement}"
        for requirement in REQUIRED_REQUIREMENTS
        if requirement.lower() not in text
    ]


def markers(path: Path, values: tuple[str, ...], label: str) -> list[str]:
    if not path.exists():
        return [f"missing {label}: {path.relative_to(ROOT)}"]
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [f"{label} missing marker: {value}" for value in values if value not in text]


def source_contract_failures() -> list[str]:
    failures: list[str] = []
    failures.extend(
        markers(
            PI_ROOT / "koalablue" / "dualeye_tts.py",
            (
                'WILLIAM_VOICE = "en-AU-WilliamNeural"',
                'SPOKEN_IDENTITY = "KillerKoala"',
                "sanitize_spoken_identity",
                "_edge_tts_pcm",
                "_espeak_pcm",
            ),
            "DualEye TTS contract",
        )
    )
    failures.extend(
        markers(
            PI_ROOT / "koalablue" / "killerkoala_hybrid_companion.py",
            (
                'DEFAULT_MODEL = "killerkoala-tinyllama:latest"',
                'mode=os.getenv("KILLERKOALA_LLM_MODE", "tinyllama")',
                "local conversational cyberpet",
                "William is only the hidden Australian male",
                "conversation_history.json",
                "research_question",
            ),
            "KillerKoala TinyLlama contract",
        )
    )
    failures.extend(
        markers(
            PI_ROOT / "koalablue" / "killerkoala_web_research.py",
            (
                "BRAVE_SEARCH_API_KEY",
                "api.duckduckgo.com",
                "en.wikipedia.org/w/api.php",
                "KILLERKOALA_WEB_SEARCH",
            ),
            "KillerKoala web-research contract",
        )
    )
    failures.extend(
        markers(
            PI_ROOT / "koalablue" / "killerkoala_expression.py",
            ("class KillerKoalaExpression", '"angry"', '"happy"', '"curious"', '"focused"'),
            "KillerKoala expression contract",
        )
    )
    failures.extend(
        markers(
            ROOT / "training" / "killerkoala_lora" / "Modelfile.killerkoala-tinyllama",
            (
                "FROM tinyllama:1.1b",
                "gruff, cheeky, cyberpunk",
                "William is only the hidden Australian male",
            ),
            "TinyLlama Modelfile",
        )
    )
    return failures


def safe_smoke() -> dict[str, Any]:
    old_mode = os.environ.get("KILLERKOALA_LLM_MODE")
    old_web = os.environ.get("KILLERKOALA_WEB_SEARCH")
    old_history = os.environ.get("KILLERKOALA_DIALOGUE_TURNS")
    os.environ["KILLERKOALA_LLM_MODE"] = "off"
    os.environ["KILLERKOALA_WEB_SEARCH"] = "off"
    os.environ["KILLERKOALA_DIALOGUE_TURNS"] = "0"
    try:
        from koalablue.dualeye_tts import SPOKEN_IDENTITY, WILLIAM_VOICE, sanitize_spoken_identity
        from koalablue.esp32_dualeye_speech_synced_bridge import ESP32DualEyeVoiceBridge
        from koalablue.killerkoala_expression import classify_response_expression
        from koalablue.killerkoala_hybrid_companion import companion_response, load_config
        from koalablue.killerkoala_voice_control import execute_module, module_manifest, parse_voice_command
        from koalablue.killerkoala_web_research import looks_like_general_question

        manifest = module_manifest()
        help_parsed = parse_voice_command("killerkoala voice commands", require_wake_word=True)
        question_parsed = parse_voice_command(
            "killerkoala what is the current Raspberry Pi operating system release",
            require_wake_word=True,
        )
        question_result = execute_module(question_parsed, force_flexible_banter=True)
        response = companion_response(
            "status",
            xp=100,
            user_text="Pi readiness check",
            flexible=False,
            history_path=None,
        )
        happy = classify_response_expression("Bonza, the action completed successfully.", status="success")
        angry = classify_response_expression("The system fault is unacceptable and blocked.", status="error")
        sanitized = sanitize_spoken_identity("G'day, I am William.")
        config = load_config()
        return {
            "wake_word": manifest.get("wake_word"),
            "module_count": len(manifest.get("modules", {})),
            "help_module_present": "killerkoala_help" in manifest.get("modules", {}),
            "question_module_present": "killerkoala_question" in manifest.get("modules", {}),
            "help_module_key": help_parsed.module_key,
            "question_module_key": question_parsed.module_key,
            "question_detector": looks_like_general_question("what is the latest firmware?"),
            "question_result_status": question_result.status,
            "question_fallback_text": question_result.companion_line,
            "companion_source": response.source,
            "companion_text": response.text,
            "companion_rank": response.rank,
            "default_model": config.model,
            "william_voice_backend": WILLIAM_VOICE,
            "spoken_identity": SPOKEN_IDENTITY,
            "sanitized_identity_sample": sanitized,
            "speech_synced_bridge_class": ESP32DualEyeVoiceBridge.__name__,
            "happy_expression": happy.to_payload(),
            "angry_expression": angry.to_payload(),
        }
    finally:
        for name, value in (
            ("KILLERKOALA_LLM_MODE", old_mode),
            ("KILLERKOALA_WEB_SEARCH", old_web),
            ("KILLERKOALA_DIALOGUE_TURNS", old_history),
        ):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main() -> int:
    parser = argparse.ArgumentParser(description="Check current KillerKoala Pi AI, web, expression, and William TTS readiness")
    parser.add_argument("--strict", action="store_true", help="Require local TTS host commands as well as Python runtime")
    parser.add_argument("--status-path", default=str(STATUS_PATH))
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []
    failures.extend(f"missing current KillerKoala runtime file: {path}" for path in missing_files())
    failures.extend(requirement_failures())
    failures.extend(source_contract_failures())
    imports, import_failures = import_status()
    failures.extend(import_failures)

    edge_tts = command_path("edge-tts")
    ffmpeg = command_path("ffmpeg")
    espeak = command_path("espeak-ng") or command_path("espeak")
    for label, value in (("edge-tts", edge_tts), ("ffmpeg", ffmpeg), ("espeak fallback", espeak)):
        if not value:
            message = f"local TTS host command unavailable: {label}"
            if args.strict:
                failures.append(message)
            else:
                warnings.append(message)

    try:
        smoke = safe_smoke()
        if smoke.get("wake_word") != "killerkoala":
            failures.append("KillerKoala voice manifest wake word is not killerkoala")
        if not smoke.get("help_module_present") or smoke.get("help_module_key") != "killerkoala_help":
            failures.append("KillerKoala help phrase did not route to killerkoala_help")
        if not smoke.get("question_module_present") or smoke.get("question_module_key") != "killerkoala_question":
            failures.append("Open-ended question did not route to killerkoala_question")
        if not smoke.get("question_detector"):
            failures.append("General-question detector rejected a current-information question")
        if smoke.get("default_model") != "killerkoala-tinyllama:latest":
            failures.append("Default Pi model is not killerkoala-tinyllama:latest")
        if smoke.get("william_voice_backend") != "en-AU-WilliamNeural":
            failures.append("William Neural is not the configured Australian TTS backend")
        if smoke.get("spoken_identity") != "KillerKoala":
            failures.append("spoken identity is not KillerKoala")
        if "William" in str(smoke.get("sanitized_identity_sample", "")):
            failures.append("backend name William leaked through spoken-identity sanitization")
        if "William" in str(smoke.get("companion_text", "")):
            failures.append("KillerKoala companion response exposed the William backend name")
        if smoke.get("happy_expression", {}).get("tone") not in {"happy", "excited"}:
            failures.append("Happy response did not select a happy/excited display expression")
        if smoke.get("angry_expression", {}).get("tone") not in {"angry", "error"}:
            failures.append("Angry/error response did not select an angry/error display expression")
    except Exception as exc:
        smoke = {"status": "error", "error": str(exc)}
        failures.append(f"KillerKoala Pi smoke check failed: {exc}")

    payload = {
        "status": "KILLERKOALA_AI_READY" if not failures else "KILLERKOALA_AI_INCOMPLETE",
        "runtime_mode": "headless_pi_os_lite",
        "response_hierarchy": [
            "waveshare_saved_vocabulary_and_basic_responses",
            "raspberry_pi_tinyllama_for_unmatched_or_open_ended_requests",
            "web_research_context_when_internet_is_available",
            "local_phrase_fallback_if_tinyllama_is_unavailable",
        ],
        "primary_pi_model": "killerkoala-tinyllama:latest",
        "spoken_identity": "KillerKoala",
        "tts_backend": "en-AU-WilliamNeural",
        "tone_synced_displays": True,
        "firmware_validation_owner": "dedicated ESP32 and T114 source workflows",
        "network_request_performed": False,
        "microphone_required": False,
        "audio_playback_performed": False,
        "firmware_flash_performed": False,
        "required_files": list(REQUIRED_FILES),
        "imports": imports,
        "tts_commands": {"edge_tts": edge_tts, "ffmpeg": ffmpeg, "espeak": espeak},
        "smoke": smoke,
        "warnings": warnings,
        "failures": failures,
        "updated_at": time.time(),
    }
    out = Path(args.status_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "status_path": str(out),
        "warnings": warnings,
        "failures": failures,
    }, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
