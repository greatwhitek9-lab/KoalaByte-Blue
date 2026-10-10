#!/usr/bin/env python3
"""Hardware-free contract check for the optional Ultra Vision feature."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
sys.path.insert(0, str(PI_ROOT))

from koalablue.ultra_vision import dependency_status


def main() -> int:
    source = (PI_ROOT / "koalablue" / "ultra_vision.py").read_text(encoding="utf-8")
    ast.parse(source)
    status = dependency_status()
    assert status["status"] in {
        "ULTRA_VISION_READY",
        "ULTRA_VISION_OPTIONAL_DEPENDENCIES_MISSING",
    }
    assert "VideoCapture" in source
    assert "model.predict" in source
    assert "save_frame" in source
    assert "privacy_scope" in source
    print("ULTRA_VISION_SOURCE_CONTRACT_PASS")
    print(f"Optional dependencies: {status['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
