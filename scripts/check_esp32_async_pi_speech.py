#!/usr/bin/env python3
from __future__ import annotations

import threading
import time


def main() -> int:
    failures: list[str] = []

    import koalablue.esp32_async_pi_speech as async_speech

    owner_thread = threading.get_ident()
    worker_threads: list[int] = []

    class DummyBridge:
        def __init__(self) -> None:
            self.original_play_calls = 0
            self.read_calls = 0
            self.closed = False
            self.faces: list[tuple[int, str, str]] = []
            self.heltec: list[tuple[int, bool, str, str]] = []
            self.writes: list[tuple[int, dict]] = []
            self._active_error = False
            self._pending_failure_face = False
            self._koalabyte_pi_speech_active = False
            self._koalabyte_pi_speech_cooldown_until = 0.0
            self._koalabyte_speech_feedback_cooldown_seconds = 1.8

        def _play_response(self, _text: str, _channel: str) -> None:
            self.original_play_calls += 1
            time.sleep(0.5)

        def read_once(self):
            self.read_calls += 1
            return None

        def close(self) -> None:
            self.closed = True

        def _fanout_face(self, state: str, message: str = "", duration_ms: int = 0) -> None:
            self.faces.append((threading.get_ident(), state, message))

        def _heltec_speech(self, active: bool, message: str = "", channel: str = "") -> None:
            self.heltec.append((threading.get_ident(), bool(active), message, channel))

        def _write_json(self, payload: dict, **_kwargs) -> None:
            self.writes.append((threading.get_ident(), dict(payload)))

    original_synth = async_speech.synthesize_pcm16_mono_16k
    original_play = async_speech._play_pcm16_mono_16k
    original_duck = async_speech.prepare_speech_duck
    original_restore = async_speech.restore_after_speech

    try:
        def fake_synth(_text: str) -> bytes:
            worker_threads.append(threading.get_ident())
            time.sleep(0.22)
            return b"\x00\x00" * 1600

        def fake_play(_pcm: bytes, _stop_event: threading.Event) -> dict:
            worker_threads.append(threading.get_ident())
            time.sleep(0.22)
            return async_speech._result(
                status="played",
                backend="regression",
                playback_seconds=0.22,
            )

        async_speech.synthesize_pcm16_mono_16k = fake_synth
        async_speech._play_pcm16_mono_16k = fake_play
        async_speech.prepare_speech_duck = lambda: "duck-token"
        async_speech.restore_after_speech = lambda _token: None

        async_speech.install_esp32_async_pi_speech(DummyBridge)
        bridge = DummyBridge()

        started = time.monotonic()
        future = bridge._play_response("Owner loop stays responsive", "pi-ai")
        enqueue_seconds = time.monotonic() - started
        if enqueue_seconds > 0.08:
            failures.append(
                f"_play_response blocked owner loop for {enqueue_seconds:.3f}s"
            )
        if bridge.original_play_calls != 0:
            failures.append("legacy blocking _play_response was called")
        if not bridge._koalabyte_pi_speech_active:
            failures.append("speech feedback lock was not activated when speech queued")

        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            bridge.read_once()
            if future.done() and int(getattr(bridge, "_koalabyte_pi_speech_pending", 1)) == 0:
                break
            time.sleep(0.01)

        if not future.done():
            failures.append("async speech future did not complete")
        else:
            result = future.result()
            if result.get("status") != "played":
                failures.append(f"unexpected async speech result: {result}")

        if bridge.read_calls < 10:
            failures.append("owner read loop did not continue while speech worker was busy")
        if bridge._koalabyte_pi_speech_active:
            failures.append("speech feedback lock did not clear after owner drained completion")
        if bridge._koalabyte_pi_speech_cooldown_until <= time.monotonic():
            failures.append("speech feedback cooldown was not armed after playback")

        if not worker_threads or any(thread_id == owner_thread for thread_id in worker_threads):
            failures.append("synthesis/playback did not execute exclusively off owner thread")

        hardware_threads = [row[0] for row in bridge.faces]
        hardware_threads.extend(row[0] for row in bridge.heltec)
        hardware_threads.extend(row[0] for row in bridge.writes)
        if not hardware_threads:
            failures.append("no owner-thread hardware callbacks were observed")
        elif any(thread_id != owner_thread for thread_id in hardware_threads):
            failures.append("a hardware-facing callback executed from the audio worker thread")

        speech_states = [row[1] for row in bridge.heltec]
        if True not in speech_states or False not in speech_states:
            failures.append("Heltec speech start/stop was not completed on owner thread")

        audio_status = [
            payload
            for _thread_id, payload in bridge.writes
            if payload.get("type") == "pi_audio_status"
        ]
        if not audio_status:
            failures.append("async Pi audio status was not written")
        elif not audio_status[-1].get("async_owner_safe"):
            failures.append("Pi audio status did not mark owner-safe async path")

        before_suppressed = len(bridge.faces)
        bridge._active_error = True
        suppressed = bridge._play_response("raw execution failure", "pi-execution")
        if suppressed.result().get("status") != "suppressed_error_sequence":
            failures.append("error sequence no longer suppresses ordinary execution speech")
        if len(bridge.faces) != before_suppressed:
            failures.append("suppressed error speech still changed the face")
        bridge._active_error = False

        bridge.close()
        if not bridge.closed:
            failures.append("async speech close wrapper did not call original close")

    finally:
        async_speech.synthesize_pcm16_mono_16k = original_synth
        async_speech._play_pcm16_mono_16k = original_play
        async_speech.prepare_speech_duck = original_duck
        async_speech.restore_after_speech = original_restore

    if failures:
        print("ESP32 async Pi speech check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("ESP32 async Pi speech check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
