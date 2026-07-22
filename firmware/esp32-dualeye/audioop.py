"""Minimal Python 3.13-compatible PCM helpers for the DualEye build.

The standard-library :mod:`audioop` module was removed in Python 3.13.  The
DualEye voice generator only needs ``lin2ulaw`` for converting little-endian
16-bit PCM into G.711 mu-law, so keep that operation local and dependency-free.
"""

from __future__ import annotations

import struct

_MULAW_BIAS = 0x84
_MULAW_CLIP = 32635


def _sample_to_mulaw(sample: int) -> int:
    """Encode one signed 16-bit PCM sample as an 8-bit G.711 mu-law value."""

    sign = 0x80 if sample < 0 else 0
    magnitude = -sample if sample < 0 else sample
    magnitude = min(magnitude, _MULAW_CLIP) + _MULAW_BIAS

    # For biased magnitudes 0x84..0x7FFF, bit_length()-8 yields segments 0..7.
    exponent = max(0, min(7, magnitude.bit_length() - 8))
    mantissa = (magnitude >> (exponent + 3)) & 0x0F
    return (~(sign | (exponent << 4) | mantissa)) & 0xFF


def lin2ulaw(fragment: bytes | bytearray | memoryview, width: int) -> bytes:
    """Convert little-endian signed PCM samples to G.711 mu-law.

    This intentionally implements only the API used by
    ``scripts/generate_local_voice_responses.py``.  The DualEye voice pipeline
    emits mono signed 16-bit little-endian PCM, so widths other than two bytes
    are rejected rather than silently producing incorrect firmware audio.
    """

    if width != 2:
        raise ValueError("DualEye lin2ulaw supports only 16-bit PCM (width=2)")

    pcm = memoryview(fragment).cast("B")
    if len(pcm) % width:
        raise ValueError("PCM fragment length must be divisible by sample width")

    encoded = bytearray(len(pcm) // width)
    for index, (sample,) in enumerate(struct.iter_unpack("<h", pcm)):
        encoded[index] = _sample_to_mulaw(sample)
    return bytes(encoded)
