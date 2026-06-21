#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PI_ROOT = Path(__file__).resolve().parents[1] / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.anteater import run_cli


if __name__ == "__main__":
    raise SystemExit(run_cli())
