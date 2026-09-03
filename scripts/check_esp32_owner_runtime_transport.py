#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from koalablue.esp32_owner_runtime_transport import (
    install_esp32_owner_runtime_transport,
)


class FakeSerial:
    def __init__(self) -> None:
        self.is_open = True
        self.writes: list[bytes] = []
        self.flushes = 0

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def flush(self) -> None:
        self.flushes += 1


class FakeBridge:
    def __init__(self) -> None:
        self._udp_peer: Any = ("192.168.1.169", 42111)
        self._serial: FakeSerial | None = FakeSerial()
        self.udp_payloads: list[dict[str, Any]] = []
        self.udp_available = True

    def _udp_write_json(self, payload: dict[str, Any]) -> bool:
        if not self.udp_available or self._udp_peer is None:
            return False
        self.udp_payloads.append(dict(payload))
        return True

    def _serial_write_json(self, payload: dict[str, Any]) -> None:
        raise AssertionError("transport wrapper was not installed")


def main() -> int:
    install_esp32_owner_runtime_transport(FakeBridge)

    bridge = FakeBridge()
    runtime_payloads = [
        {"type": "menu_sync", "event_type": "menu_reopen"},
        {"type": "eye_style", "look": "heart"},
        {"type": "killerkoala_face", "state": "listening"},
        {"type": "simulate_voice_command", "phrase": "killerkoala status"},
        {"type": "trusted_input_activity", "source": "gpio_buttons"},
    ]
    for payload in runtime_payloads:
        bridge._serial_write_json(payload)

    assert bridge.udp_payloads == runtime_payloads
    assert bridge._serial is not None
    assert bridge._serial.writes == []

    # Provisioning/status requests remain USB-first even with a healthy UDP peer.
    bridge._serial_write_json({"type": "node_status", "request": "probe"})
    bridge._serial_write_json(
        {"type": "wifi_config", "ssid": "test", "password": "x", "pi_host": "1.2.3.4"}
    )
    assert len(bridge._serial.writes) == 2

    # Runtime traffic falls back to USB if the UDP peer is unavailable.
    bridge.udp_available = False
    bridge._serial_write_json({"type": "menu_sync", "event_type": "menu_reopen"})
    assert len(bridge._serial.writes) == 3

    # Never silently acknowledge a command when neither transport can send it.
    bridge._serial = None
    failed = False
    try:
        bridge._serial_write_json({"type": "eye_style", "look": "round"})
    except RuntimeError:
        failed = True
    assert failed

    print("ESP32 owner runtime transport: PASS")
    print("- menu/K1 display traffic uses UDP first")
    print("- voice/runtime control traffic uses UDP first")
    print("- provisioning/status remains USB first")
    print("- USB fallback is checked")
    print("- no-transport commands fail instead of being silently acknowledged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
