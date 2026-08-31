#!/usr/bin/env python3
from __future__ import annotations

import json

from koalablue.killerkoala_hybrid_companion import KillerKoalaLLMConfig, should_try_llm


def _config(mode: str = "tinyllama") -> KillerKoalaLLMConfig:
    return KillerKoalaLLMConfig(
        mode=mode,
        model="killerkoala-tinyllama:latest",
        host="http://127.0.0.1:11434",
        timeout_seconds=45.0,
        num_predict=128,
        max_response_chars=520,
        dialogue_turns=4,
        lora_expected=True,
        lora_training_doc="docs/KILLERKOALA_LORA_TRAINING.md",
        modelfile_path="training/killerkoala_lora/Modelfile.killerkoala-tinyllama",
    )


def main() -> int:
    cfg = _config()
    cases = {
        "ordinary_help": should_try_llm("inquiry_help", False, cfg),
        "ordinary_status": should_try_llm("bluez_status", False, cfg),
        "ordinary_action": should_try_llm("scan_complete", False, cfg),
        "question": should_try_llm("inquiry_question", False, cfg),
        "explicit_banter": should_try_llm("status", True, cfg),
        "disabled_question": should_try_llm("inquiry_question", False, _config("off")),
    }
    expected = {
        "ordinary_help": False,
        "ordinary_status": False,
        "ordinary_action": False,
        "question": True,
        "explicit_banter": True,
        "disabled_question": False,
    }
    failures = [key for key, value in cases.items() if value != expected[key]]
    payload = {
        "ready": not failures,
        "status": "KILLERKOALA_LLM_FASTPATH_READY" if not failures else "KILLERKOALA_LLM_FASTPATH_FAILED",
        "cases": cases,
        "expected": expected,
        "failures": failures,
        "policy": "ordinary_commands=phrase_engine; questions_or_explicit_banter=tinyllama",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
