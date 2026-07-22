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
            inbox.acknowledge()

            delivered = submit_command(
                "esp32",
                {"type": "killerkoala_face", "sequence": 2},
                bus_dir=root,
            )
            assert delivered.accepted and delivered.delivered and not delivered.queued
            live = inbox.drain()
            assert live == [{"sequence": 2, "type": "killerkoala_face"}]
            inbox.acknowledge()

            duplicate_owner_blocked = False
            try:
                JsonCommandInbox("esp32", bus_dir=root)
            except RuntimeError:
                duplicate_owner_blocked = True
            assert duplicate_owner_blocked

            # Simulate power loss after claiming but before the serial write/ack.
            submit_command(
                "esp32",
                {"type": "menu_sync", "sequence": 3},
                bus_dir=root,
            )
            claimed_before_crash = inbox.drain()
            assert claimed_before_crash == [{"sequence": 3, "type": "menu_sync"}]

        with JsonCommandInbox("esp32", bus_dir=root) as recovered:
            replay_after_crash = recovered.drain()
            assert replay_after_crash == [
                {"sequence": 3, "type": "menu_sync"}
            ]
            recovered.acknowledge()

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
            heltec.acknowledge()

        payload = {
            "status": "SERIAL_COMMAND_BUS_READY",
            "single_owner_enforced": True,
            "startup_spool_replayed": True,
            "active_owner_notified": True,
            "claim_acknowledgement_required": True,
            "crash_replay_verified": True,
            "targets": ["esp32", "heltec"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
