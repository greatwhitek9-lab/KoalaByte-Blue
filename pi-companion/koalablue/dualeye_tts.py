from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from array import array
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


def _decode_pcm_samples(data: bytes, sample_width: int) -> list[int]:
    """Decode little-endian PCM to signed 16-bit-scale integer samples."""

    if sample_width == 1:
        return [(value - 128) << 8 for value in data]
    if sample_width == 2:
        samples = array("h")
        samples.frombytes(data)
        if sys.byteorder != "little":
            samples.byteswap()
        return list(samples)
    if sample_width in {3, 4}:
        samples: list[int] = []
        shift = 8 if sample_width == 3 else 16
        for offset in range(0, len(data) - sample_width + 1, sample_width):
            value = int.from_bytes(data[offset : offset + sample_width], "little", signed=True)
            samples.append(max(-32768, min(32767, value >> shift)))
        return samples
    return []


def _mono_samples(samples: list[int], channels: int) -> list[int]:
    if channels <= 1:
        return samples
    mono: list[int] = []
    usable = len(samples) - (len(samples) % channels)
    for offset in range(0, usable, channels):
        frame = samples[offset : offset + channels]
        mono.append(int(sum(frame) / channels))
    return mono


def _resample_linear(samples: list[int], source_rate: int, target_rate: int = 16000) -> list[int]:
    if not samples or source_rate <= 0:
        return []
    if source_rate == target_rate:
        return samples
    output_length = max(1, int(round(len(samples) * target_rate / source_rate)))
    scale = source_rate / target_rate
    output: list[int] = []
    last_index = len(samples) - 1
    for output_index in range(output_length):
        position = output_index * scale
        left = min(int(position), last_index)
        right = min(left + 1, last_index)
        fraction = position - left
        value = int(round(samples[left] + (samples[right] - samples[left]) * fraction))
        output.append(max(-32768, min(32767, value)))
    return output


def _wav_to_pcm16_mono_16k(wav_bytes: bytes) -> bytes:
    """Convert uncompressed WAV bytes without the removed Python 3.13 audioop module."""

    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            if wav.getcomptype() != "NONE":
                return b""
            data = wav.readframes(wav.getnframes())
            width = wav.getsampwidth()
            channels = wav.getnchannels()
            rate = wav.getframerate()
        samples = _decode_pcm_samples(data, width)
        samples = _mono_samples(samples, channels)
        samples = _resample_linear(samples, rate, 16000)
        packed = array("h", samples)
        if sys.byteorder != "little":
            packed.byteswap()
        return packed.tobytes()
    except Exception:
        return b""


def _espeak_pcm(text: str) -> bytes:
    executable = shutil.which("espeak-ng") or shutil.which("espeak")
    if not executable:
        return b""

    preferred = os.getenv("KILLERKOALA_ESPEAK_VOICE", "en-au+m3").strip() or "en-au+m3"
    voices = list(dict.fromkeys((preferred, "en-au+m3", "en-au+m2", "en-au")))
    for voice in voices:
        try:
            result = subprocess.run(
                _espeak_command(executable, voice, text),
                capture_output=True,
                timeout=20,
                check=True,
            )
            if result.stdout:
                pcm = _wav_to_pcm16_mono_16k(result.stdout)
                if pcm:
                    return pcm
        except Exception:
            continue
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
