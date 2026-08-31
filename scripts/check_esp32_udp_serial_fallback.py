#!/usr/bin/env python3
from __future__ import annotations

import json

from koalablue.esp32_udp_serial_fallback import install_esp32_udp_serial_fallback


class DummyBridge:
    def __init__(self) -> None:
        self._udp_peer = ("192.0.2.10", 42110)
        self.serial_payloads: list[dict[str, object]] = []

    def _udp_write_json(self, payload: dict[str, object]) -> bool:
        raise OSError(101, "Network is unreachable")

    def _serial_write_json(self, payload: dict[str, object]) -> None:
        self.serial_payloads.append(dict(payload))

    def _write_json(self, payload: dict[str, object], *, prefer_udp: bool = True) -> None:
        if not (prefer_udp and self._udp_write_json(payload)):
            self._serial_write_json(payload)


def main() -> int:
    install_esp32_udp_serial_fallback(DummyBridge)
    bridge = DummyBridge()
    payload = {
        "type": "menu_sync",
        "event_type": "highlight",
        "selected_label": "Kruisin Prompt Status",
    }
    bridge._write_json(payload)

    ready = bridge.serial_payloads == [payload] and bridge._udp_peer is None
    result = {
        "ready": ready,
        "status": "ESP32_UDP_SERIAL_FALLBACK_READY" if ready else "ESP32_UDP_SERIAL_FALLBACK_FAILED",
        "udp_unreachable_is_soft_failure": True,
        "stale_udp_peer_cleared": bridge._udp_peer is None,
        "serial_fallback_payload_count": len(bridge.serial_payloads),
        "menu_payload_preserved": bridge.serial_payloads == [payload],
        "firmware_flash_required": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
