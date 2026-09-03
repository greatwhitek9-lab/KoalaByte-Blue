#!/usr/bin/env python3
from __future__ import annotations

import math
import struct

from koalablue.esp32_unconfirmed_stt_fastpath import (
    _prepare_command_pcm,
    install_esp32_unconfirmed_stt_fastpath,
)


def pcm_tone(seconds: float, amplitude: int, *, sample_rate: int = 16000, hz: float = 440.0) -> bytes:
    samples = int(seconds * sample_rate)
    values = [int(amplitude * math.sin(2.0 * math.pi * hz * index / sample_rate)) for index in range(samples)]
    return struct.pack(f"<{len(values)}h", *values)


class _GateBridge:
    def __init__(self, pcm: bytes) -> None:
        self._audio = {"gate-test": bytearray(pcm)}
        self._audio_meta = {
            "gate-test": {
                "sample_rate": 16000,
                "sample_width": 2,
                "wake_already_confirmed": False,
            }
        }
        self.diag_rows: list[tuple[str, dict[str, object]]] = []
        self.writes: list[dict[str, object]] = []

    def _finish_audio(self, payload: dict[str, object]):
        raise RuntimeError("original finish path should not run for unconfirmed gate test")

    def _diag(self, event: str, **payload: object) -> None:
        self.diag_rows.append((event, payload))

    def _write_json(self, payload: dict[str, object]) -> None:
        self.writes.append(payload)


install_esp32_unconfirmed_stt_fastpath(_GateBridge)


def main() -> int:
    low = pcm_tone(6.5, 300)
    prepared_low, low_metrics = _prepare_command_pcm(low, 16000, 2)
    if prepared_low:
        raise RuntimeError(f"noise-floor PCM unexpectedly passed gate: {low_metrics}")
    if low_metrics.get("gate_passed"):
        raise RuntimeError(f"noise-floor gate metrics are inconsistent: {low_metrics}")

    # Exercise the complete patched finish path. This specifically protects
    # against duplicate diagnostic keyword arguments and other runtime-only
    # failures that a helper-only test cannot catch.
    bridge = _GateBridge(low)
    result = bridge._finish_audio({"request_id": "gate-test"})
    if result is not None:
        raise RuntimeError(f"low-energy finish path unexpectedly returned an event: {result!r}")
    if not bridge.diag_rows:
        raise RuntimeError("low-energy finish path did not emit recognizer diagnostics")
    event, diag = bridge.diag_rows[-1]
    if event != "recognizer_decision":
        raise RuntimeError(f"unexpected diagnostic event: {event}")
    if diag.get("scope") != "unconfirmed_command_energy_gated_cached":
        raise RuntimeError(f"unexpected diagnostic scope: {diag}")
    if diag.get("prepared_pcm_bytes") != 0 or diag.get("gate_passed") is not False:
        raise RuntimeError(f"low-energy diagnostic metrics are inconsistent: {diag}")
    if not bridge.writes or bridge.writes[-1].get("reason") != "ambient_below_command_energy_gate":
        raise RuntimeError(f"low-energy finish path did not reject ambient capture: {bridge.writes}")

    prefix = pcm_tone(1.2, 260)
    speech = pcm_tone(2.1, 1800)
    suffix = pcm_tone(2.7, 260)
    full = prefix + speech + suffix
    prepared, metrics = _prepare_command_pcm(full, 16000, 2)
    if not prepared:
        raise RuntimeError(f"speech-like PCM was rejected: {metrics}")
    if not metrics.get("gate_passed"):
        raise RuntimeError(f"speech-like gate metrics are inconsistent: {metrics}")
    if len(prepared) >= len(full):
        raise RuntimeError(f"speech-like PCM was not trimmed: {metrics}")
    duration = len(prepared) / 2 / 16000
    if not 2.1 <= duration <= 3.3:
        raise RuntimeError(f"unexpected prepared speech duration {duration:.3f}s: {metrics}")

    click = bytearray(pcm_tone(2.0, 200))
    one_block = pcm_tone(0.02, 5000)
    start = 16000 * 2 // 2
    click[start : start + len(one_block)] = one_block
    prepared_click, click_metrics = _prepare_command_pcm(bytes(click), 16000, 2)
    if prepared_click:
        raise RuntimeError(f"single-block transient unexpectedly passed gate: {click_metrics}")

    print("ESP32 unconfirmed PCM energy gate check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
