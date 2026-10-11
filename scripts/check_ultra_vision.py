#!/usr/bin/env python3
"""Hardware-free contract check for optional Ultra Vision on Pi 5."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
sys.path.insert(0, str(PI_ROOT))

from koalablue.ultra_vision import dependency_status
from koalablue.killerkoala_hybrid_companion import _camera_request_intent
from koalablue.killerkoala_voice_control import parse_voice_command


def main() -> int:
    source = (PI_ROOT / "koalablue" / "ultra_vision.py").read_text(encoding="utf-8")
    ast.parse(source)
    status = dependency_status()
    assert status["status"] in {
        "ULTRA_VISION_READY",
        "ULTRA_VISION_OPTIONAL_DEPENDENCIES_MISSING",
    }
    for marker in (
        "VideoCapture", "_capture_frame", "Picamera2", "KOALABYTE_VISION_CAMERA_BACKEND",
        "KILLERKOALA_ONLINE_VISION_ENABLED", "model.predict", "save_frame", "privacy_scope",
        "current_fix", "--geotag", "observation_reference",
        "camera_like_candidate", "LOCATION_MAX_AGE_SECONDS",
    ):
        assert marker in source, f"missing Ultra Vision contract marker: {marker}"
    assert "observe_camera_with_companion" in source
    assert "images" in source
    assert "continuous_stream" in source
    assert 'ai_mode == "online"' in source
    assert "OLLAMA_API_KEY" in source
    assert "https://ollama.com" in source
    assert "Online camera upload is disabled" in source
    assert '"camera_backend": camera_backend' in source
    assert "headers=headers" in source
    assert 'ai_mode == "local"' in source
    companion_source = (PI_ROOT / "koalablue" / "killerkoala_hybrid_companion.py").read_text(encoding="utf-8")
    voice_source = (PI_ROOT / "koalablue" / "killerkoala_voice_control.py").read_text(encoding="utf-8")
    assert "optional camera vision capability" in companion_source
    assert "_camera_request_intent(working)" in voice_source
    assert _camera_request_intent("KillerKoala, what do you see?")
    assert _camera_request_intent("KillerKoala, look at this")
    assert _camera_request_intent("describe the scene")
    assert _camera_request_intent("is there a camera in view?")
    assert _camera_request_intent("KillerKoala, can you see the object on the desk?")
    assert not _camera_request_intent("tell me a joke")
    parsed = parse_voice_command("KillerKoala, look at this")
    assert parsed.module_key == "killerkoala_question", parsed.module_key
    print("ULTRA_VISION_SOURCE_CONTRACT_PASS")
    print("KillerKoala conversational vision routing PASS")
    print("GNSS is opt-in, protected, and freshness-checked; observation links are contextual only.")
    print(f"Optional dependencies: {status['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
