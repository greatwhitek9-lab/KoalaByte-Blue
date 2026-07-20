from __future__ import annotations

import audioop
import io
import os
import shutil
import subprocess
import wave


def synthesize_pcm16_mono_16k(text: str) -> bytes:
    """Return raw signed 16-bit little-endian mono PCM at 16 kHz."""
    executable = shutil.which("espeak-ng") or shutil.which("espeak")
    clean = " ".join(str(text or "").split())
    if not executable or not clean:
        return b""
    try:
        result = subprocess.run(
            [executable, "--stdout", "-v", os.getenv("KILLERKOALA_ESPEAK_VOICE", "en-au"), clean],
            capture_output=True,
            timeout=20,
            check=True,
        )
        with wave.open(io.BytesIO(result.stdout), "rb") as wav:
            data = wav.readframes(wav.getnframes())
            width = wav.getsampwidth()
            channels = wav.getnchannels()
            rate = wav.getframerate()
        if channels > 1:
            data = audioop.tomono(data, width, 0.5, 0.5)
            channels = 1
        if width != 2:
            data = audioop.lin2lin(data, width, 2)
            width = 2
        if rate != 16000:
            data, _ = audioop.ratecv(data, width, channels, rate, 16000, None)
        return data
    except Exception:
        return b""
