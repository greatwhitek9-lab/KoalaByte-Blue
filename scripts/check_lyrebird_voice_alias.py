#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATUS_PATH = ROOT / "logs" / "music_player" / "lyrebird_voice_alias_readiness.json"


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def main() -> int:
    os.environ.setdefault("KOALABYTE_MENU_SYNC", "0")

    from koalablue.killerkoala_voice_router import combined_manifest, route_voice_phrase

    failures: list[str] = []
    checked: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="koalabyte-lyrebird-voice-") as temp:
        temp_path = Path(temp)
        output_dir = temp_path / "voice"
        xp_path = temp_path / "xp.json"

        for phrase in (
            "killerkoala play music",
            "killer koala play music",
        ):
            result = route_voice_phrase(
                phrase,
                output_dir=output_dir,
                xp_path=xp_path,
            )
            payload = _jsonable(result)
            menu_action = payload.get("details", {}).get("menu_action", {})
            checked[phrase] = {
                "status": payload.get("status"),
                "command": menu_action.get("command"),
                "submenu": menu_action.get("submenu"),
                "menu_status": menu_action.get("status"),
                "companion_line": payload.get("companion_line"),
            }
            if payload.get("status") != "success":
                failures.append(f"voice alias failed for {phrase!r}: {payload}")
            if menu_action.get("command") != "submenu:music_player":
                failures.append(f"voice alias did not target Lyrebird for {phrase!r}")
            if menu_action.get("submenu") != "music_player":
                failures.append(f"voice alias returned wrong submenu for {phrase!r}")
            if menu_action.get("status") != "opened":
                failures.append(f"voice alias did not open the Lyrebird submenu for {phrase!r}")

        no_wake = route_voice_phrase(
            "play music",
            output_dir=output_dir,
            xp_path=xp_path,
        )
        no_wake_payload = _jsonable(no_wake)
        checked["wake_word_required"] = no_wake_payload.get("status")
        if no_wake_payload.get("status") != "blocked":
            failures.append("play music without the KillerKoala wake word was not blocked")

        manifest = combined_manifest()
        aliases = manifest.get("menu_voice_launch", {}).get(
            "direct_application_aliases",
            [],
        )
        checked["manifest_aliases"] = aliases
        if not any(
            isinstance(alias, dict)
            and alias.get("phrase") == "killerkoala play music"
            and alias.get("command") == "submenu:music_player"
            for alias in aliases
        ):
            failures.append("combined voice manifest is missing the Lyrebird play music alias")

    payload = {
        "status": "LYREBIRD_VOICE_ALIAS_READY" if not failures else "LYREBIRD_VOICE_ALIAS_INCOMPLETE",
        "wake_word": "killerkoala",
        "intent": "play music",
        "behavior": "open_submenu",
        "command": "submenu:music_player",
        "checked": checked,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
