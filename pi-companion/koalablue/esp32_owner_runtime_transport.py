from __future__ import annotations

import json
from typing import Any

# Commands generated while KoalaByte is running should use the network path first
# once the bridge has learned the ESP32 peer. Bench testing proved the ESP32 UDP
# command parser is healthy while USB writes from the long-lived serial-owner
# process can be accepted by pyserial without producing a visible firmware action.
# Provisioning/status requests remain USB-first because they are also used before
# Wi-Fi is configured.
USB_FIRST_TYPES = {
    "wifi_config",
    "node_status",
}


def install_esp32_owner_runtime_transport(bridge_cls: type[Any]) -> type[Any]:
    """Make owner writes UDP-first for runtime control, with checked USB fallback.

    The serial-command inbox calls ``_serial_write_json`` directly. Historically
    that forced queued K1-K8/menu/display commands down USB even after the bridge
    had a healthy UDP peer. Worse, the base method silently returns when its
    serial handle is missing, which lets the inbox acknowledge a command that was
    never sent. This wrapper gives runtime commands the same proven UDP-first
    behavior as normal bridge writes and raises on an unavailable/short USB
    fallback so the inbox keeps the command claim for replay.
    """

    if getattr(bridge_cls, "_koalabyte_owner_runtime_transport_installed", False):
        return bridge_cls

    def runtime_write_json(instance: Any, payload: dict[str, Any]) -> None:
        payload_type = str(payload.get("type") or "").strip().lower()

        if payload_type not in USB_FIRST_TYPES:
            try:
                if bool(instance._udp_write_json(payload)):
                    return
            except OSError:
                # Match the bridge's normal UDP->serial soft fallback policy.
                instance._udp_peer = None

        serial_handle = getattr(instance, "_serial", None)
        if serial_handle is None or not bool(getattr(serial_handle, "is_open", True)):
            raise RuntimeError("ESP32 runtime command has no open USB serial fallback")

        wire = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        written = serial_handle.write(wire)
        if written is not None and int(written) != len(wire):
            raise OSError(
                f"short ESP32 USB write: wrote {written} of {len(wire)} bytes"
            )
        serial_handle.flush()

    bridge_cls._serial_write_json = runtime_write_json
    bridge_cls._koalabyte_owner_runtime_transport_installed = True
    return bridge_cls


__all__ = [
    "USB_FIRST_TYPES",
    "install_esp32_owner_runtime_transport",
]
