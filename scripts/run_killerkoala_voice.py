#!/usr/bin/env python3
"""Run KillerKoala spoken-command voice control.

Use scripts/run_killerkoala_hybrid.py for direct phrase-engine / optional tiny-LLM response previews.
"""

from koalablue.killerkoala_voice_control import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli())
