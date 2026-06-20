#!/usr/bin/env python3
import os

os.environ.setdefault("KOALABYTE_TTS", "1")

from koalablue.killerkoala_boot_welcome import run_cli


if __name__ == "__main__":
    raise SystemExit(run_cli())
