#!/usr/bin/env python3
from __future__ import annotations

import math
import struct

from koalablue.esp32_unconfirmed_stt_fastpath import _prepare_command_pcm


def pcm_tone(seconds: float, amplitude: int, *, sample_rate: int = 16000, hz: float = 440.0) -> bytes:
    samples = int(seconds * sample_rate)
    values = [int(amplitude * math.sin(2.0 * math.pi * hz * index / sample_rate)) for index in range(samples)]
    return struct.pack(f"<{len(values)}h", *values)


def main() -> int:
    low = pcm_tone(6.5, 300)
    prepared_low, low_metrics = _prepare_command_pcm(low, 16000, 2)
    if prepared_low:
        raise RuntimeError(f"noise-floor PCM unexpectedly passed gate: {low_metrics}")
    if low_metrics.get("gate_passed"):
        raise RuntimeError(f"noise-floor gate metrics are inconsistent: {low_metrics}")

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
