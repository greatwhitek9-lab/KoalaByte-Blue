"""Python 3.13-compatible G.711 mu-law conversion for the DualEye build."""

from __future__ import annotations

import struct

_MULAW_BIAS = 0x84
_MULAW_CLIP = 32635


def lin2ulaw(fragment: bytes | bytearray | memoryview, width: int) -> bytes:
    if width != 2:
        raise ValueError("DualEye lin2ulaw supports only 16-bit PCM")

    pcm = memoryview(fragment).cast("B")
    if len(pcm) % 2:
        raise ValueError("PCM fragment length must be even")

    encoded = bytearray(len(pcm) // 2)
    for index, (sample,) in enumerate(struct.iter_unpack("<h", pcm)):
        sign = 0x80 if sample < 0 else 0
        magnitude = -sample if sample < 0 else sample
        magnitude = min(magnitude, _MULAW_CLIP) + _MULAW_BIAS
        exponent = max(0, min(7, magnitude.bit_length() - 8))
        mantissa = (magnitude >> (exponent + 3)) & 0x0F
        encoded[index] = (~(sign | (exponent << 4) | mantissa)) & 0xFF
    return bytes(encoded)


__all__ = ["lin2ulaw"]
