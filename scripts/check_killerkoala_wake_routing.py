#!/usr/bin/env python3
from __future__ import annotations

import json

from koalablue.killerkoala_voice_control import parse_voice_command
from koalablue.killerkoala_voice_router import canonicalize_killerkoala_wake


CASES = (
    "killer koala voice commands",
    "killerkoala voice commands",
    "hey killer koala voice commands",
    "hey killerkoala voice commands",
)


def main() -> int:
    rows = []
    failures = []
    for phrase in CASES:
        canonical = canonicalize_killerkoala_wake(phrase)
        parsed = parse_voice_command(canonical, require_wake_word=True)
        row = {
            "input": phrase,
            "canonical": canonical,
            "wake_word_detected": parsed.wake_word_detected,
            "module_key": parsed.module_key,
        }
        rows.append(row)
        if not parsed.wake_word_detected or parsed.module_key != "killerkoala_help":
            failures.append(row)

    print(
        json.dumps(
            {
                "status": (
                    "KILLERKOALA_WAKE_ROUTING_READY"
                    if not failures
                    else "KILLERKOALA_WAKE_ROUTING_FAILED"
                ),
                "ready": not failures,
                "cases": rows,
                "failures": failures,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
