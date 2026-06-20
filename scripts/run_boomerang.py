#!/usr/bin/env python3
import os

os.environ.setdefault("KOALABYTE_TTS", "1")

from koalablue.boomerang import KILLERKOALA_BOOMERANG_ALERTS, run_cli


if __name__ == "__main__":
    KILLERKOALA_BOOMERANG_ALERTS["boomerang_start"] = "BOOMerang!"
    raise SystemExit(run_cli())
