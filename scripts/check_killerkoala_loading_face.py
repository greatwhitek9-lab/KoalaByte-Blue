#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.loading_face import LOADING_WORD, jungle_loading_message, loading_word_frame, start_loading_face_sequence

STATUS_PATH = ROOT / "logs" / "killerkoala_face" / "loading_face_readiness.json"


def main() -> int:
    failures: list[str] = []
    frames = [loading_word_frame(index) for index in range(len(LOADING_WORD))]
    expected = [LOADING_WORD[: index + 1] for index in range(len(LOADING_WORD))]
    if frames != expected:
        failures.append(f"loading frames do not spell {LOADING_WORD}: {frames}")
    sample = jungle_loading_message("Koala Kan Kommander", 2)
    if "LOA" not in sample or "Koala Kan Kommander" not in sample:
        failures.append(f"loading message missing action markers: {sample}")

    runner = ROOT / "scripts" / "run_menu_screen.py"
    runner_text = runner.read_text(encoding="utf-8", errors="ignore") if runner.exists() else ""
    for marker in ["start_loading_face_sequence", "KILLERKOALA_LOADING_FACE_SENTINEL", "loading.stop()"]:
        if marker not in runner_text:
            failures.append(f"run_menu_screen.py missing loading marker: {marker}")

    seq = start_loading_face_sequence("Loading Test", enabled=False)
    seq.stop()

    payload = {
        "status": "KILLERKOALA_LOADING_FACE_READY" if not failures else "KILLERKOALA_LOADING_FACE_INCOMPLETE",
        "loading_word": LOADING_WORD,
        "frames": frames,
        "sample_message": sample,
        "requirements": [
            "KillerKoala face remains active while menu actions load",
            "Loading text spells LOADING one letter at a time",
            "Loading banner uses the shared jungle/Jumanji menu face path",
        ],
        "updated_at": time.time(),
        "failures": failures,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
