from __future__ import annotations

import audioop
import io
import os
import shutil
import subprocess
import wave


def _espeak_command(executable: str, voice: str, text: str) -> list[str]:
    return [
        executable,
        "--stdout",
        "-v",
        voice,
        "-s",
        os.getenv("KILLERKOALA_ESPEAK_SPEED", "154"),
        "-p",
        os.getenv("KILLERKOALA_ESPEAK_PITCH", "31"),
        "-a",
        os.getenv("KILLERKOALA_ESPEAK_AMPLITUDE", "178"),
        "-g",
        os.getenv("KILLERKOALA_ESPEAK_GAP", "3"),
        text,
    ]


def synthesize_pcm16_mono_16k(text: str) -> bytes:
    """Return local Australian-male speech as signed mono PCM at 16 kHz."""
    executable = shutil.which("espeak-ng") or shutil.which("espeak")
    clean = " ".join(str(text or "").split())
    if not executable or not clean:
        return b""

    preferred = os.getenv("KILLERKOALA_ESPEAK_VOICE", "en-au+m3").strip() or "en-au+m3"
    voices = list(dict.fromkeys((preferred, "en-au+m3", "en-au+m2", "en-au")))
    wav_bytes = b""
    for voice in voices:
        try:
            result = subprocess.run(
                _espeak_command(executable, voice, clean),
                capture_output=True,
                timeout=20,
                check=True,
            )
            if result.stdout:
                wav_bytes = result.stdout
                break
        except Exception:
            continue
    if not wav_bytes:
        return b""

    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
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
