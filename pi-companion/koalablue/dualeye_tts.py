from __future__ import annotations

import audioop
import io
import os
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path


WILLIAM_VOICE = "en-AU-WilliamNeural"
SPOKEN_IDENTITY = "KillerKoala"
_BACKEND_NAME_PATTERN = re.compile(r"\bWilliam\b", re.IGNORECASE)


def sanitize_spoken_identity(text: str) -> str:
    """Keep the William voice backend separate from the KillerKoala persona."""

    clean = " ".join(str(text or "").split())
    return _BACKEND_NAME_PATTERN.sub(SPOKEN_IDENTITY, clean)


def _edge_tts_pcm(text: str) -> bytes:
    executable = shutil.which("edge-tts")
    ffmpeg = shutil.which("ffmpeg")
    if not executable or not ffmpeg:
        return b""

    voice = os.getenv("KILLERKOALA_TTS_VOICE", WILLIAM_VOICE).strip() or WILLIAM_VOICE
    rate = os.getenv("KILLERKOALA_EDGE_RATE", "+4%").strip() or "+4%"
    volume = os.getenv("KILLERKOALA_EDGE_VOLUME", "+18%").strip() or "+18%"
    pitch = os.getenv("KILLERKOALA_EDGE_PITCH", "-2Hz").strip() or "-2Hz"

    try:
        with tempfile.TemporaryDirectory(prefix="killerkoala-william-") as temp:
            root = Path(temp)
            media = root / "response.mp3"
            raw = root / "response.raw"
            subprocess.run(
                [
                    executable,
                    "--voice",
                    voice,
                    f"--rate={rate}",
                    f"--volume={volume}",
                    f"--pitch={pitch}",
                    "--text",
                    text,
                    "--write-media",
                    str(media),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=45,
            )
            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(media),
                    "-af",
                    "highpass=f=75,lowpass=f=7600,loudnorm=I=-16:LRA=7:TP=-1.0",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-f",
                    "s16le",
                    str(raw),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=45,
            )
            return raw.read_bytes()
    except Exception:
        return b""


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


def _espeak_pcm(text: str) -> bytes:
    executable = shutil.which("espeak-ng") or shutil.which("espeak")
    if not executable:
        return b""

    preferred = os.getenv("KILLERKOALA_ESPEAK_VOICE", "en-au+m3").strip() or "en-au+m3"
    voices = list(dict.fromkeys((preferred, "en-au+m3", "en-au+m2", "en-au")))
    wav_bytes = b""
    for voice in voices:
        try:
            result = subprocess.run(
                _espeak_command(executable, voice, text),
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


def synthesize_pcm16_mono_16k(text: str) -> bytes:
    """Return KillerKoala speech as signed mono PCM at 16 kHz.

    William Neural is the preferred Australian male synthesis backend, never the
    spoken persona. Any accidental backend-name self-reference is rewritten to
    KillerKoala before audio generation. The legacy eSpeak path remains a
    fail-soft fallback for offline Pi operation.
    """

    clean = sanitize_spoken_identity(text)
    if not clean:
        return b""
    return _edge_tts_pcm(clean) or _espeak_pcm(clean)
