from __future__ import annotations

import asyncio
import glob
import json
import os
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .ble_event_log import BleEventDeduper, BleEventLog, normalize_ble_event
from .ble_role_coordinator import elect_ble_roles, write_role_status
from .bounded_log import append_jsonl
from .gnss_location import write_gnss_status_event, write_primary_t114_fix_event

PRIMARY_USB_PORT_HINTS = (
    "koalabyte-heltec",
    "heltec",
    "t114",
    "ht-n5262",
    "wireless_tracker",
    "wireless-tracker",
    "nrf52840",
    "usbmodem",
    "ttyacm",
)
DEFAULT_BAUD = 115200
PRIMARY_STATUS_TYPES = {
    "node_roles",
    "ble_status",
    "ble_tx_status",
    "gnss_status",
    "gnss_fix",
    "heltec_mouth_status",
    "killerkoala_tft_ack",
    "status",
    "boot",
}


def candidate_usb_ports() -> list[str]:
    ports: list[str] = []
    for pattern in (
        "/dev/koalabyte-heltec",
        "/dev/koalabyte-heltec-t114",
        "/dev/serial/by-id/*",
        "/dev/ttyACM*",
        "/dev/ttyUSB*",
        "/dev/cu.usbmodem*",
        "/dev/cu.usbserial*",
    ):
        ports.extend(sorted(glob.glob(pattern)))
    seen: set[str] = set()
    unique: list[str] = []
    for port in ports:
        if port not in seen:
            seen.add(port)
            unique.append(port)
    return unique


def discover_primary_ble_port() -> str:
    for port in candidate_usb_ports():
        lower = port.lower()
        if any(hint in lower for hint in PRIMARY_USB_PORT_HINTS):
            return port
    return ""


@dataclass
class SerialBleNode:
    name: str
    port: str
    role: str
    baud: int = DEFAULT_BAUD
    timeout: float = 0.15

    def open(self):
        import serial  # type: ignore

        return serial.Serial(
            self.port,
            baudrate=self.baud,
            timeout=self.timeout,
            write_timeout=0.35,
        )


class PiBluezSecondaryScanner:
    def __init__(self, out: queue.Queue[dict[str, Any]], enabled: bool = True) -> None:
        self.out = out
        self.enabled = enabled
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()

    def start(self) -> None:
        if not self.enabled or self.thread:
            return
        self.thread = threading.Thread(
            target=self._run_thread,
            name="koalabyte-pi-bluez-node",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_thread(self) -> None:
        try:
            asyncio.run(self._run_async())
        except Exception as exc:
            self.out.put(
                {
                    "type": "node_error",
                    "source": "raspberry-pi-bluez",
                    "role": "heltec_ble_node",
                    "message": str(exc),
                    "fallback_requested": "esp32-s3-dualeye",
                }
            )

    async def _run_async(self) -> None:
        from bleak import BleakScanner  # type: ignore

        def callback(device, advertisement_data):
            payload = {
                "type": "ble_adv_seen",
                "source": "raspberry-pi-bluez",
                "role": "heltec_ble_node",
                "transport": "bluez",
                "addr": getattr(device, "address", ""),
                "name": getattr(device, "name", None)
                or getattr(advertisement_data, "local_name", None)
                or "",
                "rssi": getattr(advertisement_data, "rssi", None),
                "service_uuids": list(
                    getattr(advertisement_data, "service_uuids", []) or []
                ),
                "manufacturer": json.dumps(
                    getattr(advertisement_data, "manufacturer_data", {}) or {},
                    sort_keys=True,
                ),
                "active_scan": False,
            }
            self.out.put(payload)

        scanner = BleakScanner(callback)
        await scanner.start()
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(0.25)
        finally:
            await scanner.stop()


class BleNodeManager:
    """Coordinate Heltec-primary BLE/GNSS with elected Pi-or-ESP32 BLE nodes.

    This service is the exclusive Heltec serial owner. It publishes a sanitized,
    atomic status snapshot so menu/status readers never reopen the T114 tty.
    """

    def __init__(
        self,
        *,
        primary_port: str = "",
        dongle_port: str = "",
        esp32_port: str = "",
        baud: int = DEFAULT_BAUD,
        log_dir: str | Path = "logs/ble_nodes",
        pi_bluez: bool = True,
    ) -> None:
        selected_primary = primary_port or dongle_port or discover_primary_ble_port()
        self.primary_ble = SerialBleNode(
            "heltec-t114-nrf52840",
            selected_primary,
            "primary_ble_controller",
            baud,
        )
        self.dongle = self.primary_ble
        # Explicit diagnostics only. Production leaves this empty because the
        # DualEye voice bridge exclusively owns ESP32 serial.
        self.esp32 = (
            SerialBleNode("esp32-s3-dualeye", esp32_port, "manual_secondary", baud)
            if esp32_port
            else None
        )
        self.log = BleEventLog(log_dir)
        self.status_path = self.log.log_dir / "t114_status_snapshot.json"
        self.status_history_path = self.log.log_dir / "t114_status_events.jsonl"
        self._t114_status: dict[str, Any] = {
            "status": "waiting_for_primary",
            "source": self.primary_ble.name,
            "port": self.primary_ble.port,
            "online": False,
            "responding": False,
            "ble_ready": False,
            "ble_scan_active": False,
            "gnss_enabled": False,
            "gnss_has_fix": False,
            "tx_status": "off",
            "tx_active": False,
            "tx_reason": "",
            "last_event_type": "",
            "error": "",
            "coordinates_persisted_here": False,
            "updated_at": time.time(),
        }
        self._write_t114_status()
        self.deduper = BleEventDeduper()
        self.secondary_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self.election = elect_ble_roles(requested_by="ble_node_manager")
        write_role_status(self.election, self.log.log_dir / "ble_role_election.json")
        self.pi_bluez = PiBluezSecondaryScanner(
            self.secondary_queue,
            enabled=pi_bluez and self.election.pi_probe.available,
        )

    def _write_t114_status(self) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self._t114_status["updated_at"] = time.time()
        temp = self.status_path.with_name(
            f".{self.status_path.name}.tmp.{os.getpid()}.{time.time_ns()}"
        )
        temp.write_text(
            json.dumps(self._t114_status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, self.status_path)
        append_jsonl(self.status_history_path, dict(self._t114_status))

    def _is_primary_payload(self, payload: dict[str, Any]) -> bool:
        return payload.get("source") in {
            "heltec-t114-nrf52840",
            "heltec-t114",
            self.primary_ble.name,
        }

    def _handle_primary_status_payload(self, payload: dict[str, Any]) -> None:
        if not self._is_primary_payload(payload):
            return
        event_type = str(payload.get("type") or "")
        if event_type == "node_error":
            self._t114_status.update(
                {
                    "status": "serial_error",
                    "online": False,
                    "responding": False,
                    "error": str(payload.get("message") or "Heltec serial error")[:240],
                    "last_event_type": event_type,
                }
            )
            self._write_t114_status()
            return
        if event_type not in PRIMARY_STATUS_TYPES and event_type != "ble_seen":
            return

        self._t114_status.update(
            {
                "status": "responding",
                "online": True,
                "responding": True,
                "port": self.primary_ble.port,
                "error": "",
                "last_event_type": event_type,
            }
        )
        if event_type == "node_roles":
            self._t114_status["ble_ready"] = True
        elif event_type == "ble_status":
            self._t114_status["ble_ready"] = bool(
                payload.get("ble_ready", self._t114_status["ble_ready"])
            )
            self._t114_status["ble_scan_active"] = bool(
                payload.get(
                    "scan_active",
                    payload.get(
                        "ble_scan_active", self._t114_status["ble_scan_active"]
                    ),
                )
            )
        elif event_type == "ble_tx_status":
            raw = str(payload.get("status") or "").lower()
            active = bool(payload.get("adv_active", False)) or raw == "started"
            self._t114_status["tx_active"] = active
            self._t114_status["tx_reason"] = str(payload.get("reason") or "")[:160]
            self._t114_status["tx_status"] = (
                "blocked" if raw == "blocked" else ("on" if active else "off")
            )
        elif event_type == "gnss_status":
            self._t114_status["gnss_enabled"] = bool(
                payload.get(
                    "enabled",
                    payload.get("gnss_ready", self._t114_status["gnss_enabled"]),
                )
            )
            self._t114_status["gnss_has_fix"] = bool(
                payload.get("has_fix", self._t114_status["gnss_has_fix"])
            )
        elif event_type == "gnss_fix":
            # Coordinates are stored only by the protected GNSS module, not here.
            self._t114_status["gnss_enabled"] = True
            self._t114_status["gnss_has_fix"] = True
        elif event_type in {"heltec_mouth_status", "killerkoala_tft_ack"}:
            self._t114_status["gnss_enabled"] = bool(
                payload.get("gnss_enabled", self._t114_status["gnss_enabled"])
            )
            self._t114_status["ble_scan_active"] = bool(
                payload.get(
                    "ble_scan_active", self._t114_status["ble_scan_active"]
                )
            )
            active = bool(payload.get("ble_tx_active", self._t114_status["tx_active"]))
            self._t114_status["tx_active"] = active
            if active:
                self._t114_status["tx_status"] = "on"
        self._write_t114_status()

    def iter_serial_json(
        self,
        nodes: Iterable[SerialBleNode],
        *,
        duration_seconds: float | None = None,
    ):
        deadline = None if duration_seconds is None else time.time() + duration_seconds
        handles = []
        try:
            for node in nodes:
                if node and node.port:
                    try:
                        handles.append((node, node.open()))
                    except Exception as exc:
                        yield {
                            "type": "node_error",
                            "source": node.name,
                            "role": node.role,
                            "message": str(exc),
                        }
            yield self.election.to_payload()
            self.pi_bluez.start()
            while deadline is None or time.time() < deadline:
                made_progress = False
                while True:
                    try:
                        payload = self.secondary_queue.get_nowait()
                        if (
                            payload.get("type") == "node_error"
                            and payload.get("source") == "raspberry-pi-bluez"
                        ):
                            election = elect_ble_roles(
                                requested_by="bluez_runtime_error"
                            )
                            write_role_status(
                                election,
                                self.log.log_dir / "ble_role_election.json",
                            )
                        yield payload
                        made_progress = True
                    except queue.Empty:
                        break
                for node, ser in handles:
                    raw = ser.readline()
                    if not raw:
                        continue
                    made_progress = True
                    try:
                        payload = json.loads(
                            raw.decode("utf-8", errors="replace").strip()
                        )
                    except Exception:
                        continue
                    payload.setdefault("source", node.name)
                    payload.setdefault("role", node.role)
                    yield payload
                if not made_progress:
                    time.sleep(0.03)
        finally:
            self.pi_bluez.stop()
            for _, ser in handles:
                try:
                    ser.close()
                except Exception:
                    pass

    def _handle_primary_gnss_payload(self, payload: dict[str, Any]) -> None:
        if not self._is_primary_payload(payload):
            return
        if payload.get("type") == "gnss_fix":
            write_primary_t114_fix_event(payload)
        elif payload.get("type") == "gnss_status":
            write_gnss_status_event(payload)

    def run(self, *, duration_seconds: float | None = None):
        nodes = [self.primary_ble]
        if self.esp32:
            nodes.append(self.esp32)

        for payload in self.iter_serial_json(nodes, duration_seconds=duration_seconds):
            self._handle_primary_status_payload(payload)
            self._handle_primary_gnss_payload(payload)
            if payload.get("type") == "ble_seen":
                payload = dict(payload)
                payload["type"] = "ble_adv_seen"
                payload.setdefault("source", "esp32-s3-dualeye")
                payload.setdefault("role", "heltec_fallback_ble_node")
            if payload.get("type") != "ble_adv_seen":
                yield payload
                continue
            event = normalize_ble_event(
                payload,
                default_source=str(payload.get("source") or "unknown"),
            )
            if self.deduper.should_emit(event):
                self.log.append(event)
                yield event
