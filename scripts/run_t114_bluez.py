#!/usr/bin/env python3
"""Run Heltec T114 nRF52840 BlueZ HCI wrapper actions."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_COMPANION = REPO_ROOT / "pi-companion"
if str(PI_COMPANION) not in sys.path:
    sys.path.insert(0, str(PI_COMPANION))

from koalablue.t114_bluez import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli())
