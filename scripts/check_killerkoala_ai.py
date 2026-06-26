#!/usr/bin/env python3
"""KillerKoala AI/voice readiness check for deployment and one-shot installs.

This check validates imports, dependency declarations, voice-command routing,
phrase-first companion fallback, optional Ollama status, ESP32-S3 DualEye
built-in mic bridge files, and required model/training files. It does not flash
firmware or require a microphone.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
STATUS_PATH = ROOT / "logs" / "killerkoala" / "killerkoala_ai_readiness.json"

REQUIRED_PYTHON_PACKAGES = [
    "httpx",
    "requests",
    "serial",
    "gpiozero",
    "pygame",
    "pyttsx3",
    "speech_recognition",
]

REQUIRED_FILES = [
    "pi-companion/koalablue/killerkoala_vocabulary.py",
    "pi-companion/koalablue/killerkoala_hybrid_companion.py",
    "pi-companion/koalablue/killerkoala_voice_control.py",
    "pi-companion/koalablue/esp32_dualeye_voice_bridge.py",
    "scripts/run_killerkoala_hybrid.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_esp32_dualeye_voice_bridge.py",
    "scripts/setup_killerkoala_ollama.sh",
    "firmware/esp32-dualeye/include/config.h",
    "firmware/esp32-dualeye/src/main.cpp",
    "training/killerkoala_lora/Modelfile.killerkoala-tinyllama",
    "docs/KILLERKOALA_LORA_TRAINING.md",
]

REQUIRED_REQUIREMENTS = [
    "httpx",
    "pyserial",
    "pyttsx3",
    "SpeechRecognition",
]

FIRMWARE_MIC_NEEDLES = [
    "ESP32S3_DUALEYE_BUILTIN_MIC",
    "esp32_s3_dualeye_builtin_mic",
    "mic_status",
    "voice_wake",
    "voice_command",
    "MIC_I2S_BCLK_PIN",
    "MIC_I2S_WS_PIN",
    "MIC_I2S_DIN_PIN",
]


def _read_requirements() -> str:
    return (PI_ROOT / "requirements.txt").read_text(encoding="utf-8")


def _missing_files(paths: Iterable[str]) -> List[str]:
    return [path for path in paths if not (ROOT / path).exists()]


def _dependency_status() -> Dict[str, Dict[str, str]]:
    status: Dict[str, Dict[str, str]] = {}
    for module_name in REQUIRED_PYTHON_PACKAGES:
        try:
            importlib.import_module(module_name)
            status[module_name] = {"status": "ok"}
        except Exception as exc:
            status[module_name] = {"status": "missing_or_unavailable", "error": str(exc)}
    return status


def _requirements_failures(requirements_text: str) -> List[str]:
    lowered = requirements_text.lower()
    failures: List[str] = []
    for name in REQUIRED_REQUIREMENTS:
        if name.lower() not in lowered:
            failures.append(f"pi-companion/requirements.txt missing AI dependency: {name}")
    return failures


def _firmware_mic_failures() -> List[str]:
    failures: List[str] = []
    combined = ""
    for path in [ROOT / "firmware/esp32-dualeye/include/config.h", ROOT / "firmware/esp32-dualeye/src/main.cpp"]:
        if path.exists():
            combined += "\n" + path.read_text(encoding="utf-8", errors="ignore")
    for needle in FIRMWARE_MIC_NEEDLES:
        if needle not in combined:
            failures.append(f"ESP32 DualEye mic bridge missing firmware marker: {needle}")
    return failures


def _safe_ai_smoke() -> Dict[str, Any]:
    old_mode = os.environ.get("KILLERKOALA_LLM_MODE")
    os.environ["KILLERKOALA_LLM_MODE"] = "off"
    try:
        from koalablue.esp32_dualeye_voice_bridge import ESP32DualEyeVoiceBridge, ESP32DualEyeVoiceEvent
        from koalablue.killerkoala_hybrid_companion import companion_response
        from koalablue.killerkoala_voice_control import execute_module, module_manifest, parse_voice_command

        companion = companion_response("status", xp=100, user_text="one-shot readiness", flexible=False)
        parsed = parse_voice_command("killerkoala voice commands", require_wake_word=True)
        result = execute_module(parsed, force_flexible_banter=False)
        manifest = module_manifest()
        bridge = ESP32DualEyeVoiceBridge(port="/dev/null")
        bridge_event = ESP32DualEyeVoiceEvent(type="voice_command", phrase="killerkoala voice commands", source="readiness_check")
        bridge_parsed = parse_voice_command(bridge_event.phrase, require_wake_word=True)
        return {
            "status": "ok" if result.status in {"success", "blocked"} else result.status,
            "wake_word": manifest.get("wake_word"),
            "module_count": len(manifest.get("modules", {})),
            "voice_manifest_has_killerkoala_help": "killerkoala_help" in manifest.get("modules", {}),
            "parsed_wake_word_detected": parsed.wake_word_detected,
            "parsed_module_key": parsed.module_key,
            "companion_source": companion.source,
            "companion_rank": companion.rank,
            "voice_result_status": result.status,
            "voice_result_module": result.module_key,
            "voice_result_artifacts": result.artifacts,
            "esp32_dualeye_bridge_class": bridge.__class__.__name__,
            "esp32_dualeye_event_phrase": bridge_event.phrase,
            "esp32_dualeye_event_routes_to": bridge_parsed.module_key,
        }
    finally:
        if old_mode is None:
            os.environ.pop("KILLERKOALA_LLM_MODE", None)
        else:
            os.environ["KILLERKOALA_LLM_MODE"] = old_mode


def _ollama_status() -> Dict[str, Any]:
    status_path = ROOT / "logs" / "killerkoala" / "ollama_setup_status.json"
    if not status_path.exists():
        return {"status": "not_checked", "path": str(status_path)}
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "unreadable", "path": str(status_path), "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check KillerKoala AI/voice readiness.")
    parser.add_argument("--strict", action="store_true", help="Fail if optional microphone/TTS imports are unavailable.")
    parser.add_argument("--status-path", default=str(STATUS_PATH))
    args = parser.parse_args()

    failures: List[str] = []
    warnings: List[str] = []

    missing = _missing_files(REQUIRED_FILES)
    failures.extend(f"missing AI file: {path}" for path in missing)

    requirements_text = _read_requirements()
    failures.extend(_requirements_failures(requirements_text))
    failures.extend(_firmware_mic_failures())

    dep_status = _dependency_status()
    for name, info in dep_status.items():
        if info["status"] != "ok":
            message = f"Python package unavailable at runtime: {name}: {info.get('error', '')}"
            if args.strict or name in {"httpx", "serial"}:
                failures.append(message)
            else:
                warnings.append(message)

    smoke: Dict[str, Any]
    try:
        smoke = _safe_ai_smoke()
        if smoke.get("wake_word") != "killerkoala":
            failures.append("KillerKoala voice manifest wake_word is not killerkoala")
        if not smoke.get("voice_manifest_has_killerkoala_help"):
            failures.append("KillerKoala voice manifest missing killerkoala_help")
        if smoke.get("parsed_module_key") != "killerkoala_help":
            failures.append("Typed voice smoke phrase did not route to killerkoala_help")
        if smoke.get("esp32_dualeye_event_routes_to") != "killerkoala_help":
            failures.append("ESP32 DualEye mic event smoke phrase did not route to killerkoala_help")
    except Exception as exc:
        smoke = {"status": "error", "error": str(exc)}
        failures.append(f"KillerKoala AI smoke check failed: {exc}")

    payload = {
        "status": "KILLERKOALA_AI_READY" if not failures else "KILLERKOALA_AI_INCOMPLETE",
        "updated_at": time.time(),
        "required_files": REQUIRED_FILES,
        "dependency_status": dep_status,
        "requirements_checked": REQUIRED_REQUIREMENTS,
        "esp32_dualeye_builtin_mic_bridge": {
            "required": True,
            "firmware_markers": FIRMWARE_MIC_NEEDLES,
            "runner": "scripts/run_esp32_dualeye_voice_bridge.py",
            "default_port_order": ["KOALABYTE_ESP32_MIC_PORT", "KOALABYTE_ESP32_FACE_PORT", "ESP32_PORT", "/dev/koalabyte-esp32-dualeye"],
        },
        "smoke": smoke,
        "ollama_status": _ollama_status(),
        "warnings": warnings,
        "failures": failures,
        "safe_check": {
            "no_microphone_required": True,
            "no_firmware_flash": True,
            "ollama_not_required_for_phrase_engine": True,
        },
    }

    out = Path(args.status_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(out), "failures": failures, "warnings": warnings}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
