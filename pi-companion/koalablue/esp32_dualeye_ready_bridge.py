from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .esp32_dualeye_voice_bridge import (
    ESP32DualEyeVoiceBridge as _IntegratedVoiceBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_vocabulary import DEFAULT_HISTORY_PATH, line_for_event


class ESP32DualEyeVoiceBridge(_IntegratedVoiceBridge):
    """Integrated bridge with one spoken legacy-vocabulary ready announcement.

    The ESP32 remains visually idle while its microphone captures candidate
    speech. The Raspberry Pi owns all synthesized speech and selects startup
    lines from the older KillerKoala vocabulary engine, including its
    rank-aware Australian phrasing and anti-repeat history.
    """

    def __init__(self, *args: Any, announce_ready: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.announce_ready = bool(announce_ready)
        self._ready_spoken = False

    def _xp_value(self) -> int:
        try:
            data = json.loads(Path(self.xp_path).read_text(encoding="utf-8"))
        except Exception:
            return 0

        def find_xp(value: Any) -> Optional[int]:
            if isinstance(value, dict):
                for key in ("xp", "total_xp", "current_xp", "experience"):
                    if key in value:
                        try:
                            return max(0, int(value[key]))
                        except (TypeError, ValueError):
                            pass
                for child in value.values():
                    found = find_xp(child)
                    if found is not None:
                        return found
            return None

        return find_xp(data) or 0

    def _ready_line(self) -> str:
        return line_for_event(
            "boot",
            xp=self._xp_value(),
            history_path=DEFAULT_HISTORY_PATH,
        ).selected_text

    def _announce_ready_once(self) -> None:
        if not self.announce_ready or self._ready_spoken:
            return
        self._ready_spoken = True
        text = self._ready_line()
        self._fanout_face("wake", "", 1800)
        self._play_response(text, "pi-ready")
        self._fanout_face("idle", "", 900)

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        event = super().handle_payload(payload)
        if str(payload.get("type", "")) == "node_status" and bool(
            payload.get("speaker_ready", payload.get("audio_ready", False))
        ):
            self._announce_ready_once()
        return event


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
