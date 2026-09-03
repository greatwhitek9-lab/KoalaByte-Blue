#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from koalablue.esp32_dualeye_local_first_bridge import (
    build_fast_local_status,
    is_fast_local_status_phrase,
)
from koalablue.killerkoala_voice_router import (
    canonicalize_short_voice_query,
    route_voice_phrase,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    expected = "killerkoala what is the current system status"
    require(
        canonicalize_short_voice_query("killer koala status") == expected,
        "short spaced wake status command did not expand to the established system-status query",
    )
    require(
        canonicalize_short_voice_query("hey killer koala status") == expected,
        "short alternate-wake status command did not expand to the established system-status query",
    )
    require(
        canonicalize_short_voice_query("killer koala bluez status")
        == "killerkoala bluez status",
        "specific BlueZ status command was incorrectly rewritten",
    )

    require(
        is_fast_local_status_phrase("killer koala status"),
        "production bridge did not recognize spaced short status phrase",
    )
    require(
        is_fast_local_status_phrase("hey killer koala status"),
        "production bridge did not recognize alternate short status phrase",
    )
    require(
        not is_fast_local_status_phrase("killer koala bluez status"),
        "production bridge stole the specific BlueZ status command",
    )

    fast = build_fast_local_status(
        {
            "wifi_ready": True,
            "mic_ready": True,
            "audio_ready": True,
            "speaker_ready": True,
            "wifi_ip": "192.0.2.10",
            "fw": "test-fw",
        }
    )
    require(fast.get("status") == "success", "healthy local status was not successful")
    require(
        fast.get("module_key") == "killerkoala_status",
        "fast local status did not use the deterministic module key",
    )
    require(fast.get("llm_used") is False, "fast local status unexpectedly used the LLM")
    require(
        fast.get("web_searched") is False,
        "fast local status unexpectedly requested web research",
    )

    degraded = build_fast_local_status(
        {
            "wifi_ready": True,
            "mic_ready": False,
            "audio_ready": True,
            "speaker_ready": True,
        }
    )
    require(
        degraded.get("status") == "warning",
        "degraded local status did not report a warning",
    )
    require(
        "microphone" in str(degraded.get("companion_line") or "").lower(),
        "degraded local status did not name the unavailable microphone",
    )

    previous = {
        name: os.environ.get(name)
        for name in (
            "KILLERKOALA_LLM_MODE",
            "KILLERKOALA_WEB_SEARCH",
            "KILLERKOALA_DIALOGUE_TURNS",
        )
    }
    os.environ["KILLERKOALA_LLM_MODE"] = "off"
    os.environ["KILLERKOALA_WEB_SEARCH"] = "off"
    os.environ["KILLERKOALA_DIALOGUE_TURNS"] = "0"
    try:
        with tempfile.TemporaryDirectory(prefix="killerkoala-status-check-") as temp:
            root = Path(temp)
            result = route_voice_phrase(
                "killer koala status",
                output_dir=root / "voice",
                xp_path=root / "xp.json",
            )
            require(result.status != "blocked", "short status command remained blocked")
            require(
                result.module_key == "killerkoala_question",
                f"short status CLI compatibility routed to unexpected module: {result.module_key}",
            )
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    print("KillerKoala short status routing check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
