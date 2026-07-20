from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Any, Mapping, Optional

from .dualeye_tts import synthesize_pcm16_mono_16k
from .killerkoala_face_bridge import emit_face, emit_speech_state
from .killerkoala_hybrid_companion import companion_response

ERROR_DIG_LOG_DIR = Path("logs/killerkoala_error_dig")
ERROR_DIG_HISTORY_PATH = ERROR_DIG_LOG_DIR / "history.json"
ERROR_DIG_EVENT_PATH = ERROR_DIG_LOG_DIR / "events.jsonl"

_FAILURE_TOKENS = ("ERROR", "FAILED", "FAILURE", "FAULT", "EXCEPTION", "BLOCKED", "SKIPPED", "DENIED")
_BANNED_OUTPUT_TERMS = (
    "idiot",
    "moron",
    "stupid",
    "dumb",
    "retard",
    "kill yourself",
    "hate you",
)
_FALLBACK_DIGS = (
    "Crikey, that command landed like a boomerang in a ceiling fan.",
    "Nice try, mate. That command took the scenic route straight into a wall.",
    "That button press had all the precision of a koala on roller skates.",
    "Bonza effort. Shame the command folded faster than a camping chair.",
    "The system says no, and it has seen tidier work from possums.",
    "Fair dinkum, that command tripped over its own shoelaces.",
    "Beauty of an attempt, mate. Pity the command forgot how computers work.",
    "That request charged in bravely and immediately misplaced the exit.",
)


def _clean(text: Any, limit: int = 220) -> str:
    return " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())[:limit]


def is_error_result(result: Mapping[str, Any] | None) -> bool:
    if not isinstance(result, Mapping):
        return False
    status = _clean(result.get("status"), 80).upper()
    return bool(result.get("error")) or any(token in status for token in _FAILURE_TOKENS)


def error_details(result: Mapping[str, Any] | None, fallback: str = "action failed") -> str:
    if not isinstance(result, Mapping):
        return fallback
    return _clean(
        result.get("error")
        or result.get("message")
        or result.get("companion_line")
        or result.get("status")
        or fallback,
        180,
    )


def _load_history() -> list[str]:
    try:
        payload = json.loads(ERROR_DIG_HISTORY_PATH.read_text(encoding="utf-8"))
        rows = payload.get("recent", []) if isinstance(payload, dict) else payload
        return [_clean(row) for row in rows if _clean(row)][-12:]
    except Exception:
        return []


def _save_history(rows: list[str]) -> None:
    ERROR_DIG_LOG_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_DIG_HISTORY_PATH.write_text(
        json.dumps({"recent": rows[-12:], "updated_at": time.time()}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _acceptable_dig(text: str, recent: set[str]) -> bool:
    clean = _clean(text, 180)
    if not clean or clean in recent:
        return False
    words = clean.split()
    if len(words) < 5 or len(words) > 24:
        return False
    lowered = clean.lower()
    if any(term in lowered for term in _BANNED_OUTPUT_TERMS):
        return False
    return True


def generate_error_dig(action: str, error: str = "") -> str:
    """Generate one short, playful dig about the failed command.

    The line may tease the action or mistake, but not the user's identity, body,
    intelligence, protected traits, or personal circumstances.
    """

    action_text = _clean(action, 80) or "that command"
    error_text = _clean(error, 120) or "runtime failure"
    recent_rows = _load_history()
    recent = set(recent_rows[-6:])
    prompt = (
        f"The user-triggered action '{action_text}' failed with '{error_text}'. "
        "Return only one clever KillerKoala Australian cyberpunk dig about the failed command, "
        "not the person. Use 8 to 18 spoken words. Keep it playful, non-abusive, and free of "
        "profanity, slurs, threats, protected-trait references, or comments about intelligence."
    )

    candidate = ""
    try:
        response = companion_response(
            "banter",
            user_text=prompt,
            context={
                "module_title": action_text,
                "status": "error_dig",
                "error": error_text,
            },
            flexible=True,
            history_path=ERROR_DIG_HISTORY_PATH,
            trace_dir=ERROR_DIG_LOG_DIR,
        )
        candidate = _clean(response.text, 180)
    except Exception:
        candidate = ""

    if not _acceptable_dig(candidate, recent):
        start = abs(hash((action_text, error_text))) % len(_FALLBACK_DIGS)
        for offset in range(len(_FALLBACK_DIGS)):
            proposed = _FALLBACK_DIGS[(start + offset) % len(_FALLBACK_DIGS)]
            if proposed not in recent:
                candidate = proposed
                break
        else:
            candidate = _FALLBACK_DIGS[start]

    recent_rows.append(candidate)
    _save_history(recent_rows)
    return candidate


def _pi_audio_command(wav_path: Path) -> tuple[Optional[list[str]], str]:
    aplay = shutil.which("aplay")
    if aplay:
        command = [aplay, "-q"]
        device = os.getenv("KOALABYTE_PI_ALSA_DEVICE", "default").strip()
        if device:
            command.extend(["-D", device])
        command.append(str(wav_path))
        return command, "alsa-aplay"

    paplay = shutil.which("paplay")
    if paplay:
        command = [paplay]
        sink = os.getenv("KOALABYTE_PI_PULSE_SINK", "").strip()
        if sink:
            command.extend(["--device", sink])
        command.append(str(wav_path))
        return command, "pulse-paplay"
    return None, "none"


def speak_on_pi(text: str) -> dict[str, Any]:
    pcm = synthesize_pcm16_mono_16k(text)
    wav_path: Optional[Path] = None
    result: dict[str, Any] = {
        "status": "unavailable",
        "speaker_owner": "raspberry-pi",
        "esp32_audio_streamed": False,
        "backend": "none",
        "message": _clean(text, 160),
        "detail": "tts_returned_empty_pcm" if not pcm else "",
    }
    try:
        if not pcm:
            return result
        with tempfile.NamedTemporaryFile(
            prefix="killerkoala-error-dig-", suffix=".wav", delete=False
        ) as temporary:
            wav_path = Path(temporary.name)
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm)

        command, backend = _pi_audio_command(wav_path)
        result["backend"] = backend
        if command is None:
            result["detail"] = "neither aplay nor paplay is installed"
            return result
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
            timeout=90,
            text=True,
        )
        if completed.returncode == 0:
            result["status"] = "played"
            result["detail"] = ""
        else:
            result["status"] = "failed"
            result["detail"] = _clean(completed.stderr, 240)
    except subprocess.TimeoutExpired:
        result["status"] = "failed"
        result["detail"] = "Pi speaker playback timed out"
    except Exception as exc:
        result["status"] = "failed"
        result["detail"] = _clean(exc, 240)
    finally:
        if wav_path is not None:
            try:
                wav_path.unlink(missing_ok=True)
            except Exception:
                pass
    return result


def _append_event(payload: Mapping[str, Any]) -> None:
    ERROR_DIG_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with ERROR_DIG_EVENT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True) + "\n")


def run_standalone_error_sequence(
    action: str,
    error: str,
    *,
    minimum_alarm_seconds: Optional[float] = None,
) -> dict[str, Any]:
    """Run the alert/dig/recovery flow outside the voice bridge.

    Used by the K1-K8/headless menu path. All display and audio operations are
    fail-soft so the menu service records the original error even if a device is
    disconnected.
    """

    started = time.monotonic()
    minimum = (
        float(os.getenv("KOALABYTE_ERROR_ALARM_SECONDS", "2.2"))
        if minimum_alarm_seconds is None
        else float(minimum_alarm_seconds)
    )
    minimum = max(0.6, min(minimum, 8.0))
    action_text = _clean(action, 80) or "KoalaByte action"
    error_text = _clean(error, 160) or "action failed"
    alert = emit_face("alarmed", error_text, duration_ms=30000)
    dig = generate_error_dig(action_text, error_text)

    remaining = minimum - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)

    cleared = emit_face("error_clear", "alarm acknowledged", duration_ms=500)
    speech_start = emit_speech_state(True, dig, channel="pi-error-dig")
    speaking_face = emit_face("speaking", dig, duration_ms=12000)
    try:
        audio = speak_on_pi(dig)
    finally:
        speech_stop = emit_speech_state(False, "", channel="pi-error-dig")
        idle = emit_face("idle", "", duration_ms=800)

    result = {
        "type": "killerkoala_error_dig_sequence",
        "status": "complete",
        "action": action_text,
        "error": error_text,
        "dig": dig,
        "minimum_alarm_seconds": minimum,
        "alert": alert,
        "cleared": cleared,
        "speech_start": speech_start,
        "speaking_face": speaking_face,
        "audio": audio,
        "speech_stop": speech_stop,
        "idle": idle,
        "heltec_final_display": "killerkoala_mouth",
        "esp32_final_display": "idle_eyes",
        "speaker_owner": "raspberry-pi",
        "completed_at": time.time(),
    }
    _append_event(result)
    return result


__all__ = [
    "error_details",
    "generate_error_dig",
    "is_error_result",
    "run_standalone_error_sequence",
    "speak_on_pi",
]
