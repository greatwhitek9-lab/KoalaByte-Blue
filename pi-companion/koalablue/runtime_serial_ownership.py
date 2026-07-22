from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .serial_command_bus import JsonCommandInbox, submit_command


def _target_for(port: str, payload: dict[str, Any]) -> str:
    explicit = str(payload.get("target_display") or "").lower()
    if "heltec" in explicit or "t114" in explicit:
        return "heltec"
    if "esp32" in explicit or "dualeye" in explicit:
        return "esp32"
    payload_type = str(payload.get("type") or "").lower()
    if payload_type in {"killerkoala_speech", "koalagotchi_status"}:
        return "heltec"
    lowered = str(port or "").lower()
    if any(token in lowered for token in ("heltec", "t114", "n5262", "nrf52840")):
        return "heltec"
    return "esp32"


def _client_serial_write(port: str, _baud: int, payload: dict[str, Any]) -> bool:
    submission = submit_command(
        _target_for(port, payload),
        dict(payload),
        queue_if_unavailable=True,
    )
    return submission.accepted


def _client_menu_write(
    port: str,
    payload: dict[str, Any],
) -> tuple[bool, str]:
    submission = submit_command(
        _target_for(port, payload),
        dict(payload),
        queue_if_unavailable=True,
    )
    return submission.accepted, submission.status


def _requeue(target: str, payloads: list[dict[str, Any]]) -> None:
    for payload in payloads[-64:]:
        submit_command(target, payload, queue_if_unavailable=True)


def install_display_command_clients() -> None:
    """Stop non-owner runtime processes from opening either board's tty."""

    from . import killerkoala_face_bridge, menu_display_sync

    if not getattr(killerkoala_face_bridge, "_serial_bus_clients_installed", False):
        original_resolve_ports = killerkoala_face_bridge._resolve_ports

        def logical_resolve_ports() -> tuple[str, str]:
            esp32_port, heltec_port = original_resolve_ports()
            return (
                esp32_port or "/dev/koalabyte-esp32-dualeye",
                heltec_port or "/dev/koalabyte-heltec",
            )

        killerkoala_face_bridge._resolve_ports = logical_resolve_ports
        killerkoala_face_bridge._serial_write = _client_serial_write
        killerkoala_face_bridge._serial_bus_clients_installed = True

    menu_display_sync._send_json_line = _client_menu_write

    # The speech-synced bridge imports both helpers by value. Update every loaded
    # binding explicitly; modules imported later receive the patched helpers.
    for name in (
        "koalablue.esp32_dualeye_voice_bridge",
        "koalablue.esp32_dualeye_speech_synced_bridge",
    ):
        module = sys.modules.get(name)
        if module is not None:
            if hasattr(module, "_serial_write"):
                setattr(module, "_serial_write", _client_serial_write)
            if hasattr(module, "_resolve_ports"):
                setattr(
                    module,
                    "_resolve_ports",
                    killerkoala_face_bridge._resolve_ports,
                )


def install_esp32_serial_owner(bridge_class: type[Any]) -> None:
    """Attach the ESP32 command inbox to the long-running voice bridge."""

    if getattr(bridge_class, "_koalabyte_serial_owner_installed", False):
        return

    original_open = bridge_class.open
    original_read_once = bridge_class.read_once
    original_close = bridge_class.close

    def drain(instance: Any) -> None:
        inbox = getattr(instance, "_koalabyte_esp32_command_inbox", None)
        if inbox is None:
            return
        retry = list(getattr(instance, "_koalabyte_esp32_command_retry", []))
        retry.extend(inbox.drain(max_items=max(0, 64 - len(retry))))
        remaining: list[dict[str, Any]] = []
        for payload in retry[:64]:
            try:
                instance._serial_write_json(payload)
            except Exception:
                remaining.append(payload)
        instance._koalabyte_esp32_command_retry = remaining[-64:]

    def owned_open(instance: Any, *args: Any, **kwargs: Any) -> Any:
        result = original_open(instance, *args, **kwargs)
        try:
            instance._koalabyte_esp32_command_inbox = JsonCommandInbox("esp32")
            instance._koalabyte_esp32_command_retry = []
            drain(instance)
        except Exception:
            try:
                original_close(instance)
            finally:
                raise
        return result

    def owned_read_once(instance: Any, *args: Any, **kwargs: Any) -> Any:
        drain(instance)
        result = original_read_once(instance, *args, **kwargs)
        drain(instance)
        return result

    def owned_close(instance: Any, *args: Any, **kwargs: Any) -> Any:
        inbox = getattr(instance, "_koalabyte_esp32_command_inbox", None)
        pending = list(getattr(instance, "_koalabyte_esp32_command_retry", []))
        if inbox is not None:
            try:
                drain(instance)
                pending = list(
                    getattr(instance, "_koalabyte_esp32_command_retry", [])
                )
                pending.extend(inbox.drain(max_items=max(0, 64 - len(pending))))
            finally:
                inbox.close()
                instance._koalabyte_esp32_command_inbox = None
        instance._koalabyte_esp32_command_retry = []
        _requeue("esp32", pending)
        return original_close(instance, *args, **kwargs)

    bridge_class.open = owned_open
    bridge_class.read_once = owned_read_once
    bridge_class.close = owned_close
    bridge_class._koalabyte_serial_owner_installed = True


class _HeltecOwnedSerial:
    def __init__(self, serial_handle: Any) -> None:
        self._serial = serial_handle
        self._inbox = JsonCommandInbox("heltec")
        self._retry: list[dict[str, Any]] = []
        self._drain_commands()

    def _drain_commands(self) -> None:
        commands = [
            *self._retry,
            *self._inbox.drain(max_items=max(0, 64 - len(self._retry))),
        ]
        self._retry = []
        for payload in commands[:64]:
            try:
                line = json.dumps(payload, separators=(",", ":")) + "\n"
                self._serial.write(line.encode("utf-8"))
                self._serial.flush()
            except Exception:
                self._retry.append(payload)
        self._retry = self._retry[-64:]

    def readline(self, *args: Any, **kwargs: Any) -> Any:
        self._drain_commands()
        value = self._serial.readline(*args, **kwargs)
        self._drain_commands()
        return value

    def close(self) -> None:
        pending = list(self._retry)
        try:
            try:
                self._drain_commands()
                pending = list(self._retry)
                pending.extend(
                    self._inbox.drain(max_items=max(0, 64 - len(pending)))
                )
            finally:
                self._inbox.close()
            _requeue("heltec", pending)
        finally:
            self._serial.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._serial, name)


def install_heltec_serial_owner() -> None:
    """Attach the Heltec command inbox to the BLE/GNSS serial manager."""

    from .ble_node_manager import SerialBleNode

    if getattr(SerialBleNode, "_koalabyte_serial_owner_installed", False):
        return
    original_open: Callable[..., Any] = SerialBleNode.open

    def owned_open(node: Any, *args: Any, **kwargs: Any) -> Any:
        serial_handle = original_open(node, *args, **kwargs)
        if node.role == "primary_ble_controller" or "heltec" in node.name.lower():
            try:
                return _HeltecOwnedSerial(serial_handle)
            except Exception:
                serial_handle.close()
                raise
        return serial_handle

    SerialBleNode.open = owned_open
    SerialBleNode._koalabyte_serial_owner_installed = True


__all__ = [
    "install_display_command_clients",
    "install_esp32_serial_owner",
    "install_heltec_serial_owner",
]
