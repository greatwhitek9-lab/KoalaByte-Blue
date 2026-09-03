#!/usr/bin/env python3
from __future__ import annotations

import time
from types import SimpleNamespace


def main() -> int:
    failures: list[str] = []

    import koalablue.esp32_misheard_voice_fastpath as fastpath
    from koalablue.menu_voice_launcher import parse_menu_voice_launch
    from koalablue.pocketsphinx_command_grammar import (
        CUSTOM_PRONUNCIATIONS,
        MENU_SHORTCUTS,
        _candidate_phrases,
    )

    class DummyBridge:
        def __init__(self) -> None:
            self.original_calls = 0
            self.faces: list[tuple[str, str, int]] = []
            self.writes: list[dict] = []
            self.played: list[tuple[str, str]] = []
            self._last_stt_search = "jsgf_commands"

        def _route_phrase(self, event):
            self.original_calls += 1
            return {"event": event, "result": {"status": "original_route"}}

        def _fanout_face(self, state: str, message: str, duration_ms: int) -> None:
            self.faces.append((state, message, duration_ms))

        def _write_json(self, payload: dict) -> None:
            self.writes.append(dict(payload))

        def _play_response(self, message: str, source: str) -> None:
            self.played.append((message, source))

    original_live = fastpath._route_live_voice_submenu
    try:
        fastpath._route_live_voice_submenu = lambda self, event: {
            "event": event,
            "result": {"status": "submenu_allowed"},
        }
        fastpath.install_esp32_misheard_voice_fastpath(DummyBridge)

        bridge = DummyBridge()
        leaf = SimpleNamespace(
            phrase="killer koala open anteater",
            source="esp32_s3_es7210_pi_wake_stt",
            request_id="leaf",
            payload={
                "wake_already_confirmed": False,
                "pi_stt_completed_at": time.time(),
            },
        )
        leaf_result = bridge._route_phrase(leaf)
        leaf_data = leaf_result.get("result", {})
        if leaf_data.get("status") != "ignored":
            failures.append("unconfirmed AntEater leaf action was not ignored")
        if not leaf_data.get("leaf_action_blocked"):
            failures.append("unconfirmed AntEater leaf action was not marked blocked")
        if bridge.original_calls != 0:
            failures.append("unconfirmed leaf action reached the normal executor")
        if not bridge.faces or bridge.faces[-1][0] != "idle":
            failures.append("unconfirmed leaf rejection did not restore idle face")
        if bridge.played:
            failures.append("unconfirmed leaf rejection spoke a response")

        stale = SimpleNamespace(
            phrase="killer koala open anteater",
            source="esp32_s3_es7210_pi_wake_stt",
            request_id="stale",
            payload={
                "wake_already_confirmed": False,
                "pi_stt_completed_at": time.time() - 30.0,
            },
        )
        stale_result = bridge._route_phrase(stale)
        if stale_result.get("result", {}).get("event_age_seconds", 0) < 20:
            failures.append("stale unconfirmed command did not carry stale age")
        if not any(row.get("reason") == "stale_unconfirmed_voice_event" for row in bridge.writes):
            failures.append("stale unconfirmed command was not rejected by stale guard")
        if bridge.original_calls != 0:
            failures.append("stale unconfirmed command reached normal executor")

        submenu = SimpleNamespace(
            phrase="killer koala open eucalyptus",
            source="esp32_s3_es7210_pi_wake_stt",
            request_id="submenu",
            payload={
                "wake_already_confirmed": False,
                "pi_stt_completed_at": time.time(),
            },
        )
        submenu_result = bridge._route_phrase(submenu)
        if submenu_result.get("result", {}).get("status") != "submenu_allowed":
            failures.append("valid unconfirmed Eucalyptus submenu navigation was blocked")

        confirmed = SimpleNamespace(
            phrase="killer koala open anteater",
            source="esp32_s3_es7210_confirmed_wake_followup",
            request_id="confirmed",
            payload={"wake_already_confirmed": True},
        )
        confirmed_result = bridge._route_phrase(confirmed)
        if confirmed_result.get("result", {}).get("status") != "original_route":
            failures.append("independently confirmed leaf action did not retain explicit execution path")
        if bridge.original_calls != 1:
            failures.append("confirmed leaf action did not reach normal executor exactly once")

    finally:
        fastpath._route_live_voice_submenu = original_live

    eucalyptus = parse_menu_voice_launch(
        "killer koala open eucalyptus",
        require_wake_word=True,
    )
    if eucalyptus is None or not eucalyptus.is_submenu or eucalyptus.command != "submenu:eucalyptus":
        failures.append("Eucalyptus voice navigation no longer resolves to its submenu")

    commander = parse_menu_voice_launch(
        "killer koala open koala kan kommander",
        require_wake_word=True,
    )
    if commander is None or commander.command != "submenu:koala_kan":
        failures.append("Koala Kan Kommander alias did not resolve to submenu:koala_kan")

    if "kan" not in CUSTOM_PRONUNCIATIONS:
        failures.append("PocketSphinx custom dictionary is missing kan pronunciation")
    shortcuts = set(MENU_SHORTCUTS.get("submenu:koala_kan", ()))
    if "koala kan kommander" not in shortcuts:
        failures.append("Koala Kan Kommander JSGF shortcut is missing")

    bad_back_rows = [
        phrase
        for phrase, is_menu in _candidate_phrases()
        if is_menu and str(phrase).lower().startswith("back to ")
    ]
    if bad_back_rows:
        failures.append(f"Back-to menu labels still leak into JSGF: {bad_back_rows[:3]}")

    if failures:
        print("ESP32 unconfirmed voice safety check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("ESP32 unconfirmed voice safety check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
