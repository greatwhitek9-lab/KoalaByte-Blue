from __future__ import annotations

from typing import Any


def install_esp32_udp_serial_fallback(bridge_cls: type[Any]) -> type[Any]:
    """Make stale/unreachable ESP32 UDP peers fall back to USB serial.

    The base bridge prefers UDP once it has seen a peer. If that peer later
    becomes unreachable, socket.sendto raises OSError and previously aborted the
    entire display/result write before _write_json could use its serial fallback.
    Treat transport loss as a soft failure: clear the stale peer and return
    False so the existing _write_json path writes the same payload over USB.
    """

    if getattr(bridge_cls, "_koalabyte_udp_serial_fallback_installed", False):
        return bridge_cls

    original_udp_write_json = bridge_cls._udp_write_json

    def udp_write_json_with_serial_fallback(instance: Any, payload: dict[str, Any]) -> bool:
        try:
            return bool(original_udp_write_json(instance, payload))
        except OSError:
            instance._udp_peer = None
            return False

    bridge_cls._udp_write_json = udp_write_json_with_serial_fallback
    bridge_cls._koalabyte_udp_serial_fallback_installed = True
    return bridge_cls


__all__ = ["install_esp32_udp_serial_fallback"]
