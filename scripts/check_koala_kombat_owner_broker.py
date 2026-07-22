#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="koalabyte-kombat-broker-") as temp:
        root = Path(temp)
        bus_dir = root / "bus"
        esp32_events = root / "esp32_events.jsonl"
        heltec_events = root / "heltec_events.jsonl"
        os.environ["KOALABYTE_SERIAL_BUS_DIR"] = str(bus_dir)
        os.environ["KOALABYTE_NODE_EVENTS_PATH"] = str(esp32_events)
        os.environ["KOALABYTE_BLE_EVENTS_PATH"] = str(heltec_events)
        os.environ["KOALA_KOMBAT_MAX_BROKER_SCAN_SECONDS"] = "1"

        from koalablue.serial_command_bus import JsonCommandInbox
        from koalablue import koala_kombat_kruisin as kombat
        from koalablue import koala_kombat_runtime_broker as broker

        # Constants are evaluated at import; keep the test explicit and isolated.
        broker.ESP32_EVENTS_PATH = esp32_events
        broker.HELTEC_EVENTS_PATH = heltec_events
        broker.MAX_BROKER_SCAN_SECONDS = 1.0

        now = time.time()
        esp32_events.write_text(
            json.dumps(
                {
                    "type": "wifi_ap_seen",
                    "source": "esp32-s3-dualeye",
                    "bssid": "redacted",
                    "bssid_fingerprint": "0123456789abcdef",
                    "ssid": "test-network",
                    "rssi": -52,
                    "received_at": now,
                    "transport": "esp32-wifi-scan",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        heltec_events.write_text(
            json.dumps(
                {
                    "type": "ble_adv_seen",
                    "source": "heltec-t114-nrf52840",
                    "addr": "AA:BB:CC:DD:EE:FF",
                    "name": "test-beacon",
                    "rssi": -66,
                    "last_seen_ts": now,
                    "transport": "heltec-primary",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        with JsonCommandInbox("esp32", bus_dir=bus_dir) as esp32_inbox, JsonCommandInbox(
            "heltec", bus_dir=bus_dir
        ) as heltec_inbox:
            events, notes = kombat._read_serial_node_events(
                duration_seconds=1,
                include_wifi=True,
                include_ble=True,
            )
            esp32_commands = esp32_inbox.drain()
            heltec_commands = heltec_inbox.drain()
            esp32_inbox.acknowledge()
            heltec_inbox.acknowledge()

        assert any(command.get("type") == "scan_nodes" for command in esp32_commands)
        assert any(command.get("type") == "ble_status" for command in heltec_commands)
        assert len(events) == 2
        assert any("no serial tty was opened" in note for note in notes)

        records = [
            kombat._node_event_to_record(
                event,
                None,
                include_wifi=True,
                include_ble=True,
            )
            for event in events
        ]
        records = [record for record in records if record is not None]
        assert len(records) == 2
        wifi = next(record for record in records if record.radio == "wifi")
        assert wifi.identifier == "hash:0123456789abcdef"
        assert kombat._node_ports() == {
            "esp32": str(bus_dir / "esp32.sock"),
            "heltec": str(bus_dir / "heltec.sock"),
        }

        print(
            json.dumps(
                {
                    "status": "KOALA_KOMBAT_OWNER_BROKER_READY",
                    "serial_tty_opened": False,
                    "esp32_scan_command_brokered": True,
                    "heltec_status_command_brokered": True,
                    "bounded_ledgers_read": True,
                    "redacted_identifier_fingerprinted": True,
                    "event_count": len(events),
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
