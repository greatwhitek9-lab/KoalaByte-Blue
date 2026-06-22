#!/usr/bin/env python3
"""Run KillerKoala spoken-command voice control.

The Heltec branch uses koalablue.killerkoala_voice_face_control so the wake word,
AI interaction, and selected voice action can show the split KillerKoala koala face.
The wrapper delegates command parsing and module execution to koalblue.killerkoala_voice_control.
"""

from koalablue.killerkoala_voice_face_control import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli())
