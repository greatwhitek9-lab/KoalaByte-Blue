from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

LOADING_WORD = "LOADING"
LOADING_INTERVAL_SECONDS = 0.38
LOADING_DURATION_MS = 1400
JUNGLE_LOADING_LEFT = "<<"
JUNGLE_LOADING_RIGHT = ">>"


def _short(text: str, limit: int = 54) -> str:
    clean = " ".join(str(text or "").split())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "..."


def loading_word_frame(step: int = 0, word: str = LOADING_WORD) -> str:
    """Return the letter-by-letter loading word frame: L, LO, LOA ... LOADING."""
    clean = "".join(ch for ch in str(word or LOADING_WORD).upper() if ch.isalnum()) or LOADING_WORD
    index = max(0, int(step)) % len(clean)
    return clean[: index + 1]


def loading_step_for_started_at(started_at: float, now: Optional[float] = None, interval: float = LOADING_INTERVAL_SECONDS) -> int:
    t = time.time() if now is None else float(now)
    return max(0, int((t - float(started_at)) / max(0.05, float(interval))))


def jungle_loading_message(action_title: str = "", step: int = 0) -> str:
    """Jungle/Jumanji-style loading banner for face displays and terminal text."""
    word = loading_word_frame(step)
    suffix = _short(action_title)
    banner = f"{JUNGLE_LOADING_LEFT} {word} {JUNGLE_LOADING_RIGHT}"
    return banner if not suffix else f"{banner} {suffix}"


@dataclass
class LoadingFaceSequence:
    action_title: str = ""
    interval_seconds: float = LOADING_INTERVAL_SECONDS
    duration_ms: int = LOADING_DURATION_MS
    enabled: bool = True
    _stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False, repr=False)

    def start(self) -> "LoadingFaceSequence":
        if not self.enabled or self._thread is not None:
            return self
        self._thread = threading.Thread(target=self._run, name="koalabyte-loading-face", daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        step = 0
        while not self._stop.is_set():
            try:
                from .killerkoala_face_bridge import emit_face
                emit_face("loading", jungle_loading_message(self.action_title, step), duration_ms=self.duration_ms)
            except Exception:
                pass
            step += 1
            self._stop.wait(max(0.05, float(self.interval_seconds)))

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=0.8)

    def __enter__(self) -> "LoadingFaceSequence":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()


def start_loading_face_sequence(action_title: str = "", *, enabled: bool = True) -> LoadingFaceSequence:
    return LoadingFaceSequence(action_title=action_title, enabled=enabled).start()
