#!/usr/bin/env python3
"""Validate the current Pi-side KillerKoala AI, voice, and TTS contract.

Firmware implementation details are validated by the dedicated ESP32 workflow.
This gate checks only the Raspberry Pi OS Lite runtime and performs no network
request, microphone capture, firmware flash, or audio playback.
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
    "pi-companion/koalablue/killerkoala_hybrid_companion.py",
    "pi-companion/koalablue/killerkoala_voice_control.py",
    "pi-companion/koalablue/dualeye_tts.py",
    "pi-companion/koalablue/esp32_dualeye_voice_bridge.py",
    "pi-companion/koalablue/esp32_dualeye_latched_koalagotchi_bridge.py",
    "scripts/run_killerkoala_hybrid.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_esp32_dualeye_voice_bridge.py",
)

REQUIRED_IMPORTS = (
    "httpx",
    "requests",
    "serial",
    "pyttsx3",
    "speech_recognition",
    "koalablue.killerkoala_vocabulary",
    "koalablue.killerkoala_hybrid_companion",
    "koalablue.killerkoala_voice_control",
    "koalablue.dualeye_tts",
    "koalablue.esp32_dualeye_latched_koalagotchi_bridge",
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


def source_contract_failures() -> list[str]:
    failures: list[str] = []
    tts_text = (PI_ROOT / "koalablue" / "dualeye_tts.py").read_text(encoding="utf-8", errors="ignore")
    for marker in (
        'WILLIAM_VOICE = "en-AU-WilliamNeural"',
        'SPOKEN_IDENTITY = "KillerKoala"',
        "sanitize_spoken_identity",
        "_edge_tts_pcm",
        "_espeak_pcm",
    ):
        if marker not in tts_text:
            failures.append(f"DualEye TTS contract missing marker: {marker}")

    companion_text = (PI_ROOT / "koalablue" / "killerkoala_hybrid_companion.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    for marker in (
        "Your identity and spoken name are always KillerKoala",
        "William is only the hidden Australian",
        "text-to-speech backend",
        "sanitize_spoken_identity",
    ):
        if marker not in companion_text:
            failures.append(f"KillerKoala identity contract missing marker: {marker}")
    return failures


def safe_smoke() -> dict[str, Any]:
    old_mode = os.environ.get("KILLERKOALA_LLM_MODE")
    old_web = os.environ.get("KILLERKOALA_WEB_SEARCH")
    os.environ["KILLERKOALA_LLM_MODE"] = "off"
    os.environ["KILLERKOALA_WEB_SEARCH"] = "off"
    try:
        from koalablue.dualeye_tts import SPOKEN_IDENTITY, WILLIAM_VOICE, sanitize_spoken_identity
        from koalablue.esp32_dualeye_latched_koalagotchi_bridge import ESP32DualEyeVoiceBridge
        from koalablue.killerkoala_hybrid_companion import companion_response
        from koalablue.killerkoala_voice_control import module_manifest, parse_voice_command

        manifest = module_manifest()
        parsed = parse_voice_command("killerkoala voice commands", require_wake_word=True)
        response = companion_response(
            "status",
            xp=100,
            user_text="Pi readiness check",
            flexible=False,
            history_path=None,
        )
        sanitized = sanitize_spoken_identity("G'day, I am William.")
        return {
            "wake_word": manifest.get("wake_word"),
            "module_count": len(manifest.get("modules", {})),
            "help_module_present": "killerkoala_help" in manifest.get("modules", {}),
            "parsed_wake_word_detected": parsed.wake_word_detected,
            "parsed_module_key": parsed.module_key,
            "companion_source": response.source,
            "companion_text": response.text,
            "companion_rank": response.rank,
            "william_voice_backend": WILLIAM_VOICE,
            "spoken_identity": SPOKEN_IDENTITY,
            "sanitized_identity_sample": sanitized,
            "latched_bridge_class": ESP32DualEyeVoiceBridge.__name__,
        }
    finally:
        if old_mode is None:
            os.environ.pop("KILLERKOALA_LLM_MODE", None)
        else:
            os.environ["KILLERKOALA_LLM_MODE"] = old_mode
        if old_web is None:
            os.environ.pop("KILLERKOALA_WEB_SEARCH", None)
        else:
            os.environ["KILLERKOALA_WEB_SEARCH"] = old_web


def main() -> int:
    parser = argparse.ArgumentParser(description="Check current KillerKoala Pi AI and William TTS readiness")
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

    smoke: dict[str, Any]
    try:
        smoke = safe_smoke()
        if smoke.get("wake_word") != "killerkoala":
            failures.append("KillerKoala voice manifest wake word is not killerkoala")
        if not smoke.get("help_module_present"):
            failures.append("KillerKoala voice manifest is missing killerkoala_help")
        if not smoke.get("parsed_wake_word_detected") or smoke.get("parsed_module_key") != "killerkoala_help":
            failures.append("KillerKoala typed voice-help phrase did not route to killerkoala_help")
        if smoke.get("william_voice_backend") != "en-AU-WilliamNeural":
            failures.append("William Neural is not the configured Australian TTS backend")
        if smoke.get("spoken_identity") != "KillerKoala":
            failures.append("spoken identity is not KillerKoala")
        if "William" in str(smoke.get("sanitized_identity_sample", "")):
            failures.append("backend name William leaked through spoken-identity sanitization")
        if "William" in str(smoke.get("companion_text", "")):
            failures.append("KillerKoala companion response exposed the William backend name")
    except Exception as exc:
        smoke = {"status": "error", "error": str(exc)}
        failures.append(f"KillerKoala Pi smoke check failed: {exc}")

    payload = {
        "status": "KILLERKOALA_AI_READY" if not failures else "KILLERKOALA_AI_INCOMPLETE",
        "runtime_mode": "headless_pi_os_lite",
        "firmware_validation_owner": "dedicated ESP32 source workflow",
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
