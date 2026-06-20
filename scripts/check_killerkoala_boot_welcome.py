#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from koalablue.killerkoala_boot_welcome import (
    KILLERKOALA_BOOT_WELCOME_LINES,
    resolve_boot_mode,
    speak_boot_welcome,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        preboot = root / "preboot_mode_selection.json"
        dongle = root / "dongle_mode_state.json"
        log = root / "boot_welcome_alerts.jsonl"

        preboot.write_text(json.dumps({"selected_mode": "koalabyte_lab", "selection_source": "test"}), encoding="utf-8")
        mode, source = resolve_boot_mode(preboot_state_path=preboot, dongle_state_path=dongle)
        assert mode == "koalabyte_lab"
        assert source == "test"
        lab_payload = speak_boot_welcome(mode="koalabyte_lab", tts_enabled=False, welcome_log=log)
        assert "Lab Mode is loaded" in lab_payload["line"]

        adapter_payload = speak_boot_welcome(mode="external adaptor", tts_enabled=False, welcome_log=log)
        assert adapter_payload["mode"] == "koala_konnect"
        assert "External adaptor mode is loaded" in adapter_payload["line"]

        unknown_payload = speak_boot_welcome(mode="mystery", tts_enabled=False, welcome_log=log)
        assert unknown_payload["mode"] == "unknown"
        assert KILLERKOALA_BOOT_WELCOME_LINES["unknown"] == unknown_payload["line"]

        events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        assert [event["mode"] for event in events] == ["koalabyte_lab", "koala_konnect", "unknown"]
    print("KillerKoala boot welcome smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
