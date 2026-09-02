#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from pathlib import Path

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
                f"short status command routed to unexpected module: {result.module_key}",
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
