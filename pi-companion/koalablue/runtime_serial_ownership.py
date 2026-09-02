from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .serial_command_bus import JsonCommandInbox, submit_command

HELTEC_MAX_LINE_BYTES = 255


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


def _wire_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def compact_heltec_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the exact bounded JSON object written to the T114 USB parser."""

    payload_type = str(payload.get("type") or "")[:40]
    if payload_type in {"killerkoala_face", "ai_face", "ai_face_sync"}:
        compact: dict[str, Any] = {
            "type": "killerkoala_face",
            "state": str(payload.get("state") or "idle")[:31],
            "message": str(payload.get("message") or "")[:92],
            "duration_ms": max(
                250,
                min(int(payload.get("duration_ms") or 4500), 30000),
            ),
            "enabled": bool(payload.get("enabled", True)),
        }
        display_mode = str(payload.get("display_mode") or "")
        if display_mode in {"koalagotchi_action", "jungle_loading_banner"}:
            compact["display_mode"] = display_mode
        if "frame_index" in payload:
            compact["frame_index"] = max(
                0, min(int(payload.get("frame_index") or 0), 255)
            )
        if payload.get("action_title"):
            compact["action_title"] = str(payload.get("action_title") or "")[:32]
        if "progress" in payload:
            compact["progress"] = max(
                -1, min(int(payload.get("progress") or 0), 100)
            )
        for key, limit in (
            ("tone", 23),
            ("subject", 27),
            ("speech_motion", 27),
            ("mouth_expression", 31),
        ):
            if payload.get(key):
                compact[key] = str(payload.get(key) or "")[:limit]
        if "intensity" in payload:
            compact["intensity"] = max(
                20, min(int(payload.get("intensity") or 60), 100)
            )
    elif payload_type == "killerkoala_speech":
        compact = {
            "type": payload_type,
            "active": bool(payload.get("active", False)),
            "message": str(payload.get("message") or "")[:92],
        }
        for key, limit in (
            ("tone", 23),
            ("subject", 27),
            ("speech_motion", 27),
            ("mouth_expression", 31),
        ):
            if payload.get(key):
                compact[key] = str(payload.get(key) or "")[:limit]
        if "intensity" in payload:
            compact["intensity"] = max(
                20, min(int(payload.get("intensity") or 60), 100)
            )
    elif payload_type == "koalagotchi_status":
        compact = {
            "type": payload_type,
            "health": max(
                0,
                min(
                    int(
                        payload.get("health")
                        or payload.get("contentment")
                        or 0
                    ),
                    100,
                ),
            ),
            "mood": str(payload.get("mood") or "calm")[:47],
            "expression": str(payload.get("expression") or "smile")[:31],
        }
    elif payload_type == "ble_lab_advertise_start":
        compact = {
            "type": payload_type,
            "name": str(payload.get("name") or "KoalaByte-T114")[:20],
            "duration_ms": max(
                1000,
                min(int(payload.get("duration_ms") or 30000), 60000),
            ),
        }
    elif payload_type in {
        "status",
        "heltec_mouth_status",
        "gnss_status",
        "gnss_current_fix",
        "gnss_fix",
        "lora_status",
        "ble_status",
        "ble_tx_status",
        "ble_lab_advertise_stop",
        "node_roles",
    }:
        compact = {"type": payload_type}
    else:
        compact = {
            key: value
            for key, value in payload.items()
            if key not in {"target_display", "source", "transport"}
        }

    wire = _wire_bytes(compact)
    if len(wire) > HELTEC_MAX_LINE_BYTES and "message" in compact:
        message = str(compact.get("message") or "")
        while message and len(wire) > HELTEC_MAX_LINE_BYTES:
            over = len(wire) - HELTEC_MAX_LINE_BYTES
            message = message[: max(0, len(message) - max(1, over))]
            compact["message"] = message
            wire = _wire_bytes(compact)
    if len(wire) > HELTEC_MAX_LINE_BYTES:
        raise ValueError(
            f"Heltec command {payload_type or '<missing-type>'} is "
            f"{len(wire)} bytes; maximum is {HELTEC_MAX_LINE_BYTES}"
        )
    return compact


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
    """Attach the crash-resilient ESP32 inbox to the voice bridge."""

    if getattr(bridge_class, "_koalabyte_serial_owner_installed", False):
        return

    original_open = bridge_class.open
    original_read_once = bridge_class.read_once
    original_close = bridge_class.close

    def drain(instance: Any) -> None:
        inbox = getattr(instance, "_koalabyte_esp32_command_inbox", None)
        if inbox is None:
            return
        commands = inbox.drain(max_items=64)
        if not commands:
            return
        for payload in commands:
            try:
                instance._serial_write_json(payload)
            except Exception:
                # Leave the active claim unacknowledged. The same batch is replayed
                # after the owner recovers or restarts; duplicate display commands
                # are safer than silent command loss.
                return
        inbox.acknowledge()

    def owned_open(instance: Any, *args: Any, **kwargs: Any) -> Any:
        result = original_open(instance, *args, **kwargs)
        try:
            instance._koalabyte_esp32_command_inbox = JsonCommandInbox("esp32")
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
        if inbox is not None:
            try:
                drain(instance)
            finally:
                inbox.close()
                instance._koalabyte_esp32_command_inbox = None
        return original_close(instance, *args, **kwargs)

    bridge_class.open = owned_open
    bridge_class.read_once = owned_read_once
    bridge_class.close = owned_close
    bridge_class._koalabyte_serial_owner_installed = True


class _HeltecOwnedSerial:
    def __init__(self, serial_handle: Any) -> None:
        self._serial = serial_handle
        self._inbox = JsonCommandInbox("heltec")
        self._drain_commands()

    def _drain_commands(self) -> None:
        commands = self._inbox.drain(max_items=64)
        if not commands:
            return
        transient_failure = False
        for payload in commands:
            try:
                wire_payload = compact_heltec_payload(payload)
                self._serial.write(_wire_bytes(wire_payload) + b"\n")
                self._serial.flush()
            except ValueError as exc:
                # An invalid oversized command can never succeed on retry. Log it
                # and continue so it cannot permanently block later valid commands.
                print(f"Rejected unsafe Heltec serial payload: {exc}", file=sys.stderr)
            except Exception:
                transient_failure = True
                break
        if not transient_failure:
            self._inbox.acknowledge()

    def readline(self, *args: Any, **kwargs: Any) -> Any:
        self._drain_commands()
        value = self._serial.readline(*args, **kwargs)
        self._drain_commands()
        return value

    def close(self) -> None:
        try:
            self._drain_commands()
        finally:
            self._inbox.close()
            self._serial.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._serial, name)


def install_heltec_serial_owner() -> None:
    """Attach the crash-resilient Heltec inbox to the BLE/GNSS manager."""

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
    "HELTEC_MAX_LINE_BYTES",
    "compact_heltec_payload",
    "install_display_command_clients",
    "install_esp32_serial_owner",
    "install_heltec_serial_owner",
]
