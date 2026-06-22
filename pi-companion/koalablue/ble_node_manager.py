from __future__ import annotations

import asyncio
import glob
import json
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .ble_event_log import BleEventDeduper, BleEventLog, normalize_ble_event

USB_PORT_HINTS = ("nrf52840", "pca10059", "dongle", "adafruit", "usbmodem", "ttyacm")
DEFAULT_BAUD = 115200


def candidate_usb_ports() -> list[str]:
    ports: list[str] = []
    for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*", "/dev/cu.usbmodem*", "/dev/cu.usbserial*"):
        ports.extend(sorted(glob.glob(pattern)))
    seen: set[str] = set()
    unique: list[str] = []
    for port in ports:
        if port not in seen:
            seen.add(port)
            unique.append(port)
    return unique


def discover_dongle_port() -> str:
    for port in candidate_usb_ports():
        lower = port.lower()
        if any(hint in lower for hint in USB_PORT_HINTS):
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

        return serial.Serial(self.port, baudrate=self.baud, timeout=self.timeout, write_timeout=0.35)


class PiBluezSecondaryScanner:
    def __init__(self, out: queue.Queue[dict[str, Any]], enabled: bool = True) -> None:
        self.out = out
        self.enabled = enabled
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()

    def start(self) -> None:
        if not self.enabled or self.thread:
            return
        self.thread = threading.Thread(target=self._run_thread, name="koalabyte-pi-bluez-secondary", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_thread(self) -> None:
        try:
            asyncio.run(self._run_async())
        except Exception as exc:
            self.out.put({"type": "node_error", "source": "raspberry-pi-bluez", "role": "secondary", "message": str(exc)})

    async def _run_async(self) -> None:
        from bleak import BleakScanner  # type: ignore

        def callback(device, advertisement_data):
            payload = {
                "type": "ble_adv_seen",
                "source": "raspberry-pi-bluez",
                "role": "secondary",
                "transport": "bluez",
                "addr": getattr(device, "address", ""),
                "name": getattr(device, "name", None) or getattr(advertisement_data, "local_name", None) or "",
                "rssi": getattr(advertisement_data, "rssi", None),
                "service_uuids": list(getattr(advertisement_data, "service_uuids", []) or []),
                "manufacturer": json.dumps(getattr(advertisement_data, "manufacturer_data", {}) or {}, sort_keys=True),
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
    """Coordinate main-branch BLE node roles.

    The Nordic nRF52840 USB Dongle is the primary BLE source. ESP32-S3 DualEye
    and Raspberry Pi BlueZ observations are secondary/fallback evidence. The
    deduper resolves duplicate observations in favor of Dongle-origin events.
    """

    def __init__(
        self,
        *,
        dongle_port: str = "",
        esp32_port: str = "",
        baud: int = DEFAULT_BAUD,
        log_dir: str | Path = "logs/ble_nodes",
        pi_bluez: bool = True,
    ) -> None:
        self.dongle = SerialBleNode("nrf52840-dongle", dongle_port or discover_dongle_port(), "primary", baud)
        self.esp32 = SerialBleNode("esp32-s3-dualeye", esp32_port, "secondary", baud) if esp32_port else None
        self.log = BleEventLog(log_dir)
        self.deduper = BleEventDeduper()
        self.secondary_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self.pi_bluez = PiBluezSecondaryScanner(self.secondary_queue, enabled=pi_bluez)

    def iter_serial_json(self, nodes: Iterable[SerialBleNode], *, duration_seconds: float | None = None):
        deadline = None if duration_seconds is None else time.time() + duration_seconds
        handles = []
        try:
            for node in nodes:
                if node and node.port:
                    try:
                        handles.append((node, node.open()))
                    except Exception as exc:
                        yield {"type": "node_error", "source": node.name, "role": node.role, "message": str(exc)}
            self.pi_bluez.start()
            while deadline is None or time.time() < deadline:
                made_progress = False
                while True:
                    try:
                        yield self.secondary_queue.get_nowait()
                        made_progress = True
                    except queue.Empty:
                        break
                for node, ser in handles:
                    raw = ser.readline()
                    if not raw:
                        continue
                    made_progress = True
                    try:
                        payload = json.loads(raw.decode("utf-8", errors="replace").strip())
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

    def run(self, *, duration_seconds: float | None = None):
        nodes = [self.dongle]
        if self.esp32:
            nodes.append(self.esp32)

        for payload in self.iter_serial_json(nodes, duration_seconds=duration_seconds):
            if payload.get("type") == "ble_seen":
                payload = dict(payload)
                payload["type"] = "ble_adv_seen"
                payload.setdefault("source", "esp32-s3-dualeye")
                payload.setdefault("role", "secondary")
            if payload.get("type") != "ble_adv_seen":
                yield payload
                continue
            event = normalize_ble_event(payload, default_source=str(payload.get("source") or "unknown"))
            if self.deduper.should_emit(event):
                self.log.append(event)
                yield event
