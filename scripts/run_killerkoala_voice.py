#!/usr/bin/env python3
"""Run KillerKoala spoken-command voice control.

Supports both direct KillerKoala voice modules and menu/submenu launch phrases:

  killerkoala run <menu item or command>
  killerkoala open <menu item or command>

Use scripts/run_killerkoala_hybrid.py for direct phrase-engine / optional tiny-LLM response previews.
"""

from koalablue.killerkoala_voice_router import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli())
