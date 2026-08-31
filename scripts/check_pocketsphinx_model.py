#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.esp32_dualeye_sphinx_bridge import validate_pocketsphinx_decoder


def main() -> int:
    result = validate_pocketsphinx_decoder()
    payload = {
        "status": "POCKETSPHINX_MODEL_READY" if result.get("ready") else "POCKETSPHINX_MODEL_INVALID",
        **result,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
