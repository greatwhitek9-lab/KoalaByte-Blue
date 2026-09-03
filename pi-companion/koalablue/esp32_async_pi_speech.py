from __future__ import annotations

import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from concurrent.futures import Future
from pathlib import Path
from typing import Any

from .dualeye_tts import synthesize_pcm16_mono_16k
from .mopidy_player import prepare_speech_duck, restore_after_speech

_DEFAULT_QUEUE_MAX = max(
    1,
    min(int(os.getenv("KOALABYTE_PI_SPEECH_QUEUE_MAX", "1")), 4),
)
_DEFAULT_QUEUE_MAX_AGE_SECONDS = max(
    0.5,
    min(float(os.getenv("KOALABYTE_PI_SPEECH_MAX_QUEUE_AGE_SECONDS", "3.0")), 10.0),
)
_DEFAULT_PLAYBACK_TIMEOUT_SECONDS = max(
    5.0,
    min(float(os.getenv("KOALABYTE_PI_SPEECH_PLAYBACK_TIMEOUT_SECONDS", "90")), 120.0),
)
_READY_ACK_TIMEOUT_SECONDS = 0.35
_SENTINEL = object()


def _result(
    *,
    status: str,
    backend: str = "none",
    detail: str = "",
    synthesis_seconds: float = 0.0,
    playback_seconds: float = 0.0,
    queue_delay_seconds: float = 0.0,
) -> dict[str, Any]:
    return {
        "status": status,
        "backend": backend,
        "detail": detail,
        "synthesis_seconds": round(max(0.0, synthesis_seconds), 3),
        "playback_seconds": round(max(0.0, playback_seconds), 3),
        "queue_delay_seconds": round(max(0.0, queue_delay_seconds), 3),
    }


def _completed_future(payload: dict[str, Any]) -> Future[dict[str, Any]]:
    future: Future[dict[str, Any]] = Future()
    future.set_result(payload)
    return future


def _audio_command(wav_path: Path) -> tuple[list[str] | None, str]:
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


def _play_pcm16_mono_16k(
    pcm: bytes,
    stop_event: threading.Event,
) -> dict[str, Any]:
    if not pcm:
        return _result(status="unavailable", detail="tts_returned_empty_pcm")

    wav_path: Path | None = None
    started = time.monotonic()
    process: subprocess.Popen[str] | None = None
    backend = "none"
    try:
        with tempfile.NamedTemporaryFile(
            prefix="killerkoala-pi-response-",
            suffix=".wav",
            delete=False,
        ) as temporary:
            wav_path = Path(temporary.name)

        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm)

        command, backend = _audio_command(wav_path)
        if command is None:
            return _result(
                status="unavailable",
                backend=backend,
                detail="neither aplay nor paplay is installed",
            )

        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + _DEFAULT_PLAYBACK_TIMEOUT_SECONDS
        while process.poll() is None:
            if stop_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=0.5)
                return _result(
                    status="cancelled",
                    backend=backend,
                    detail="voice bridge closing",
                    playback_seconds=time.monotonic() - started,
                )
            if time.monotonic() >= deadline:
                process.kill()
                process.wait(timeout=0.5)
                return _result(
                    status="failed",
                    backend=backend,
                    detail="Pi speaker playback timed out",
                    playback_seconds=time.monotonic() - started,
                )
            time.sleep(0.04)

        stderr = ""
        if process.stderr is not None:
            try:
                stderr = process.stderr.read() or ""
            except Exception:
                stderr = ""
        if int(process.returncode or 0) == 0:
            return _result(
                status="played",
                backend=backend,
                playback_seconds=time.monotonic() - started,
            )
        return _result(
            status="failed",
            backend=backend,
            detail=" ".join(stderr.split())[:240],
            playback_seconds=time.monotonic() - started,
        )
    except Exception as exc:
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except Exception:
                pass
        return _result(
            status="failed",
            backend=backend,
            detail=str(exc)[:240],
            playback_seconds=time.monotonic() - started,
        )
    finally:
        if wav_path is not None:
            try:
                wav_path.unlink(missing_ok=True)
            except Exception:
                pass


def _ensure_runtime(instance: Any) -> None:
    thread = getattr(instance, "_koalabyte_pi_speech_thread", None)
    if thread is not None and bool(getattr(thread, "is_alive", lambda: False)()):
        return

    requests: queue.Queue[Any] = queue.Queue(maxsize=_DEFAULT_QUEUE_MAX)
    owner_events: queue.Queue[dict[str, Any]] = queue.Queue()
    stop_event = threading.Event()
    state_lock = threading.Lock()

    instance._koalabyte_pi_speech_requests = requests
    instance._koalabyte_pi_speech_owner_events = owner_events
    instance._koalabyte_pi_speech_stop_event = stop_event
    instance._koalabyte_pi_speech_state_lock = state_lock
    instance._koalabyte_pi_speech_pending = 0

    def worker() -> None:
        while not stop_event.is_set():
            try:
                item = requests.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is _SENTINEL:
                return

            future: Future[dict[str, Any]] = item["future"]
            text = str(item["text"])
            channel = str(item["channel"])
            submitted_at = float(item["submitted_at"])
            queue_delay = max(0.0, time.monotonic() - submitted_at)

            if queue_delay > _DEFAULT_QUEUE_MAX_AGE_SECONDS:
                payload = _result(
                    status="skipped_stale",
                    detail="speech response expired before playback",
                    queue_delay_seconds=queue_delay,
                )
                owner_events.put(
                    {
                        "type": "done",
                        "text": text,
                        "channel": channel,
                        "result": payload,
                    }
                )
                if not future.done():
                    future.set_result(payload)
                continue

            synth_started = time.monotonic()
            try:
                pcm = synthesize_pcm16_mono_16k(text)
            except Exception as exc:
                pcm = b""
                synth_error = str(exc)[:240]
            else:
                synth_error = ""
            synthesis_seconds = time.monotonic() - synth_started

            if not pcm:
                payload = _result(
                    status="unavailable",
                    detail=synth_error or "tts_returned_empty_pcm",
                    synthesis_seconds=synthesis_seconds,
                    queue_delay_seconds=queue_delay,
                )
                owner_events.put(
                    {
                        "type": "done",
                        "text": text,
                        "channel": channel,
                        "result": payload,
                    }
                )
                if not future.done():
                    future.set_result(payload)
                continue

            ready_ack = threading.Event()
            owner_events.put(
                {
                    "type": "ready",
                    "text": text,
                    "channel": channel,
                    "ack": ready_ack,
                }
            )
            ready_ack.wait(timeout=_READY_ACK_TIMEOUT_SECONDS)

            duck_token: Any = None
            try:
                duck_token = prepare_speech_duck()
            except Exception:
                duck_token = None
            try:
                payload = _play_pcm16_mono_16k(pcm, stop_event)
            finally:
                try:
                    restore_after_speech(duck_token)
                except Exception:
                    pass

            payload["synthesis_seconds"] = round(synthesis_seconds, 3)
            payload["queue_delay_seconds"] = round(queue_delay, 3)
            owner_events.put(
                {
                    "type": "done",
                    "text": text,
                    "channel": channel,
                    "result": payload,
                }
            )
            if not future.done():
                future.set_result(payload)

    thread = threading.Thread(
        target=worker,
        name="koalabyte-pi-speech",
        daemon=True,
    )
    instance._koalabyte_pi_speech_thread = thread
    thread.start()


def _audio_status_payload(text: str, channel: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "pi_audio_status",
        "status": str(result.get("status") or "unknown"),
        "backend": str(result.get("backend") or "none"),
        "channel": channel,
        "speaker_owner": "raspberry-pi",
        "esp32_audio_streamed": False,
        "message": " ".join(str(text).split())[:96],
        "detail": str(result.get("detail") or "")[:240],
        "synthesis_seconds": result.get("synthesis_seconds", 0.0),
        "playback_seconds": result.get("playback_seconds", 0.0),
        "queue_delay_seconds": result.get("queue_delay_seconds", 0.0),
        "async_owner_safe": True,
    }


def _drain_owner_events(instance: Any) -> int:
    owner_events = getattr(instance, "_koalabyte_pi_speech_owner_events", None)
    if owner_events is None:
        return 0
    drained = 0
    while True:
        try:
            event = owner_events.get_nowait()
        except queue.Empty:
            break
        drained += 1
        event_type = str(event.get("type") or "")
        text = str(event.get("text") or "")
        channel = str(event.get("channel") or "pi-ai")

        if event_type == "ready":
            try:
                instance._heltec_speech(True, text, channel)
                instance._fanout_face("speaking", text, 12000)
            finally:
                ack = event.get("ack")
                if hasattr(ack, "set"):
                    ack.set()
            continue

        if event_type != "done":
            continue

        try:
            instance._heltec_speech(False, "", channel)
        except Exception:
            pass
        result = dict(event.get("result") or {})
        try:
            instance._write_json(_audio_status_payload(text, channel, result))
        except Exception:
            pass
        if channel == "pi-error-dig":
            instance._pending_failure_face = False

        lock = getattr(instance, "_koalabyte_pi_speech_state_lock", None)
        if lock is None:
            instance._koalabyte_pi_speech_pending = max(
                0,
                int(getattr(instance, "_koalabyte_pi_speech_pending", 1)) - 1,
            )
            pending = int(instance._koalabyte_pi_speech_pending)
        else:
            with lock:
                instance._koalabyte_pi_speech_pending = max(
                    0,
                    int(getattr(instance, "_koalabyte_pi_speech_pending", 1)) - 1,
                )
                pending = int(instance._koalabyte_pi_speech_pending)

        if pending == 0:
            instance._koalabyte_pi_speech_active = False
            cooldown = float(
                getattr(instance, "_koalabyte_speech_feedback_cooldown_seconds", 1.8)
            )
            instance._koalabyte_pi_speech_cooldown_until = time.monotonic() + cooldown
    return drained


def install_esp32_async_pi_speech(bridge_cls: type[Any]) -> type[Any]:
    """Move William synthesis/playback off the ESP32 serial-owner routing loop.

    The worker is intentionally audio-only. ESP32/Heltec writes are represented as
    owner events and drained by ``read_once`` on the bridge owner thread. This
    keeps K1/menu/display traffic responsive while TTS synthesis or ``aplay`` is
    busy and preserves the exclusive serial-owner invariant.
    """

    if getattr(bridge_cls, "_koalabyte_async_pi_speech_installed", False):
        return bridge_cls

    original_play_response = bridge_cls._play_response
    original_read_once = bridge_cls.read_once
    original_close = bridge_cls.close

    def async_play_response(instance: Any, text: str, channel: str) -> Future[dict[str, Any]]:
        if os.getenv("KOALABYTE_ASYNC_PI_SPEECH", "1").strip().lower() in {
            "0",
            "false",
            "no",
            "off",
        }:
            original_play_response(instance, text, channel)
            return _completed_future(_result(status="legacy_sync"))

        if (
            str(channel or "").startswith("pi-")
            and channel != "pi-error-dig"
            and (
                bool(getattr(instance, "_active_error", False))
                or bool(getattr(instance, "_pending_failure_face", False))
            )
        ):
            return _completed_future(
                _result(status="suppressed_error_sequence", detail="error dig owns speech")
            )

        clean = " ".join(str(text or "").split())
        if not clean:
            return _completed_future(_result(status="skipped_empty"))

        _ensure_runtime(instance)
        future: Future[dict[str, Any]] = Future()
        request = {
            "future": future,
            "text": clean,
            "channel": str(channel or "pi-ai"),
            "submitted_at": time.monotonic(),
        }

        requests = instance._koalabyte_pi_speech_requests
        try:
            requests.put_nowait(request)
        except queue.Full:
            payload = _result(
                status="dropped_busy",
                detail="speech queue full; stale delayed response suppressed",
            )
            future.set_result(payload)
            try:
                instance._write_json(_audio_status_payload(clean, str(channel), payload))
            except Exception:
                pass
            return future

        lock = instance._koalabyte_pi_speech_state_lock
        with lock:
            instance._koalabyte_pi_speech_pending = int(
                getattr(instance, "_koalabyte_pi_speech_pending", 0)
            ) + 1
        instance._koalabyte_pi_speech_active = True

        # Give immediate visual acknowledgement, but leave T114 speech-motion
        # activation to the owner-thread READY event when PCM is actually ready.
        instance._fanout_face("speaking", clean, 12000)
        return future

    def async_read_once(instance: Any, *args: Any, **kwargs: Any) -> Any:
        _drain_owner_events(instance)
        result = original_read_once(instance, *args, **kwargs)
        _drain_owner_events(instance)
        return result

    def async_close(instance: Any, *args: Any, **kwargs: Any) -> Any:
        _drain_owner_events(instance)
        stop_event = getattr(instance, "_koalabyte_pi_speech_stop_event", None)
        if stop_event is not None:
            stop_event.set()
        requests = getattr(instance, "_koalabyte_pi_speech_requests", None)
        if requests is not None:
            try:
                requests.put_nowait(_SENTINEL)
            except queue.Full:
                pass
        if bool(getattr(instance, "_koalabyte_pi_speech_active", False)):
            try:
                instance._heltec_speech(False, "", "pi-close")
            except Exception:
                pass
        instance._koalabyte_pi_speech_active = False
        return original_close(instance, *args, **kwargs)

    bridge_cls._play_response = async_play_response
    bridge_cls.read_once = async_read_once
    bridge_cls.close = async_close
    bridge_cls._koalabyte_async_pi_speech_installed = True
    bridge_cls._koalabyte_async_pi_speech_owner_safe = True
    return bridge_cls


__all__ = [
    "install_esp32_async_pi_speech",
]
