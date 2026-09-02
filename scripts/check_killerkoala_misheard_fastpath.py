#!/usr/bin/env python3
from __future__ import annotations

from koalablue.esp32_misheard_voice_fastpath import should_fast_clarify_misheard_phrase


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(
        should_fast_clarify_misheard_phrase("killer koala that's not", "jsgf_commands"),
        "unsupported JSGF wake fragment did not select fast clarification",
    )
    require(
        not should_fast_clarify_misheard_phrase("killer koala status", "jsgf_commands"),
        "exact short status was incorrectly intercepted",
    )
    require(
        not should_fast_clarify_misheard_phrase("killer koala bluez status", "jsgf_commands"),
        "supported command was incorrectly intercepted",
    )
    require(
        not should_fast_clarify_misheard_phrase(
            "killer koala what is bluetooth low energy", "jsgf_commands"
        ),
        "general question was incorrectly intercepted",
    )
    require(
        not should_fast_clarify_misheard_phrase("killer koala chat", "jsgf_commands"),
        "explicit conversational request was incorrectly intercepted",
    )
    require(
        not should_fast_clarify_misheard_phrase("killer koala that's not", "general_lm"),
        "non-command recognizer output was incorrectly intercepted",
    )

    print("KillerKoala misheard-command fastpath check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
