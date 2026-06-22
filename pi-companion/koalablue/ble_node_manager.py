from __future__ import annotations

import glob
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .ble_event_log import BleEventDeduper, BleEventLog, normalize_ble_event


USB_PORT_HINTS = ("heltec", "t114", "ht-n5262", "nrf52840", "adafruit", "usbmodem", "ttyacm")
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


def discover_heltec_port() -> str:
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

    def send(self, payload: dict[str, Any]) -> bool:
        if not self.port:
            return False
        try:
            with self.open() as ser:
                ser.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
                ser.flush()
            return True
        except Exception:
            return False


class BleNodeManager:
    """Coordinate KoalaByte BLE node roles.

    The Heltec T114 nRF52840 is the primary BLE source. ESP32-S3 and Raspberry
    Pi BlueZ observations can be folded in as secondary evidence, but duplicate
    observations are resolved in favor of Heltec-origin events.
    """

    def __init__(
        self,
        *,
        heltec_port: str = "",
        esp32_port: str = "",
        baud: int = DEFAULT_BAUD,
        log_dir: str | Path = "logs/ble_nodes",
    ) -> None:
        self.heltec = SerialBleNode("heltec-t114", heltec_port or discover_heltec_port(), "primary", baud)
        self.esp32 = SerialBleNode("esp32-s3-dualeye", esp32_port, "secondary", baud) if esp32_port else None
        self.log = BleEventLog(log_dir)
        self.deduper = BleEventDeduper()

    def start_heltec_primary(self, *, active_scan: bool = False) -> bool:
        return self.heltec.send({"type": "ble_start", "role": "primary", "active_scan": bool(active_scan)})

    def stop_heltec_primary(self) -> bool:
        return self.heltec.send({"type": "ble_stop"})

    def request_heltec_status(self) -> bool:
        return self.heltec.send({"type": "ble_status"})

    def set_secondary_role(self, node: SerialBleNode) -> bool:
        return node.send({"type": "ble_set_role", "role": "secondary"})

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
            while deadline is None or time.time() < deadline:
                made_progress = False
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
            for _, ser in handles:
                try:
                    ser.close()
                except Exception:
                    pass

    def run(self, *, duration_seconds: float | None = None, active_scan: bool = False, start_primary: bool = True):
        if self.esp32:
            self.set_secondary_role(self.esp32)
        if start_primary:
            self.start_heltec_primary(active_scan=active_scan)

        nodes = [self.heltec]
        if self.esp32:
            nodes.append(self.esp32)

        for payload in self.iter_serial_json(nodes, duration_seconds=duration_seconds):
            if payload.get("type") != "ble_adv_seen":
                yield payload
                continue
            event = normalize_ble_event(payload, default_source=str(payload.get("source") or "unknown"))
            if self.deduper.should_emit(event):
                self.log.append(event)
                yield event
