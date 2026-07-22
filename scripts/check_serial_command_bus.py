#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from koalablue.serial_command_bus import JsonCommandInbox, submit_command


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="koalabyte-serial-bus-") as temp:
        root = Path(temp)

        queued = submit_command(
            "esp32",
            {"type": "menu_sync", "sequence": 1},
            bus_dir=root,
        )
        assert queued.accepted and queued.queued and not queued.delivered

        with JsonCommandInbox("esp32", bus_dir=root) as inbox:
            replay = inbox.drain()
            assert replay == [{"sequence": 1, "type": "menu_sync"}]

            delivered = submit_command(
                "esp32",
                {"type": "killerkoala_face", "sequence": 2},
                bus_dir=root,
            )
            assert delivered.accepted and delivered.delivered and not delivered.queued
            live = inbox.drain()
            assert live == [{"sequence": 2, "type": "killerkoala_face"}]

            duplicate_owner_blocked = False
            try:
                JsonCommandInbox("esp32", bus_dir=root)
            except RuntimeError:
                duplicate_owner_blocked = True
            assert duplicate_owner_blocked

        with JsonCommandInbox("heltec", bus_dir=root) as heltec:
            submitted = submit_command(
                "heltec",
                {"type": "killerkoala_speech", "active": True},
                bus_dir=root,
            )
            assert submitted.delivered
            assert heltec.drain() == [
                {"active": True, "type": "killerkoala_speech"}
            ]

        payload = {
            "status": "SERIAL_COMMAND_BUS_READY",
            "single_owner_enforced": True,
            "startup_spool_replayed": True,
            "live_datagram_delivered": True,
            "targets": ["esp32", "heltec"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
