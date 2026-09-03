#!/usr/bin/env python3
from __future__ import annotations

from types import SimpleNamespace

from koalablue import hdmi_display_state
from koalablue.esp32_misheard_voice_fastpath import _route_live_voice_submenu


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


class DummyBridge:
    def __init__(self) -> None:
        self.writes: list[dict[str, object]] = []
        self.spoken: list[tuple[str, str]] = []

    def _write_json(self, payload):
        self.writes.append(dict(payload))

    def _play_response(self, text: str, channel: str) -> None:
        self.spoken.append((text, channel))


def main() -> int:
    submitted: list[tuple[str, str]] = []
    original_submit = hdmi_display_state.submit_menu_command

    def fake_submit(command: str, *, source: str = "hdmi", root=None):
        submitted.append((command, source))
        return {"command": command, "source": source, "submitted_at": 1.0}

    hdmi_display_state.submit_menu_command = fake_submit
    try:
        cases = (
            ("killer koala menu", "main_menu", "main"),
            ("killer koala kruisin", "submenu:kruisin", "kruisin"),
        )
        for index, (phrase, expected_command, expected_menu) in enumerate(cases, start=1):
            bridge = DummyBridge()
            event = SimpleNamespace(
                phrase=phrase,
                request_id=str(index),
                payload={},
                source="test",
                type="voice_command",
            )
            result = _route_live_voice_submenu(bridge, event)
            require(result is not None, f"live menu fastpath did not match: {phrase}")
            data = result.get("result", {})
            require(data.get("status") == "success", f"live menu failed: {phrase}: {data}")
            require(data.get("live_menu_command") == expected_command, f"wrong live command for {phrase}: {data}")
            menu_writes = [row for row in bridge.writes if row.get("type") == "menu_sync"]
            require(menu_writes, f"no immediate menu_sync emitted for {phrase}")
            require(menu_writes[-1].get("menu_name") == expected_menu, f"wrong menu payload for {phrase}: {menu_writes[-1]}")
            require(bridge.spoken, f"no deterministic acknowledgement for {phrase}")
            require(bridge.spoken[-1][1] == "pi-menu-navigation", f"wrong speech channel for {phrase}")

        require(
            submitted == [
                ("main_menu", "killerkoala_voice"),
                ("submenu:kruisin", "killerkoala_voice"),
            ],
            f"live menu queue mismatch: {submitted}",
        )
    finally:
        hdmi_display_state.submit_menu_command = original_submit

    print("KillerKoala live voice-menu check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
