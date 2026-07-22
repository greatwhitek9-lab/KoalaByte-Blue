#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from koalablue.runtime_serial_ownership import (
    HELTEC_MAX_LINE_BYTES,
    compact_heltec_payload,
)
from koalablue.serial_command_bus import (
    JsonCommandInbox,
    owner_is_active,
    submit_command,
)


def wire_length(payload: dict[str, object]) -> int:
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="koalabyte-serial-bus-") as temp:
        root = Path(temp)

        rejected = submit_command(
            "heltec",
            {"type": "ble_lab_advertise_start", "confirm": True},
            queue_if_unavailable=False,
            bus_dir=root,
        )
        assert not rejected.accepted
        assert not rejected.delivered
        assert not rejected.queued
        assert rejected.status == "owner_unavailable_not_queued"
        assert not (root / "heltec.queue.jsonl").exists()
        assert not owner_is_active("heltec", root)

        queued = submit_command(
            "esp32",
            {"type": "menu_sync", "sequence": 1},
            bus_dir=root,
        )
        assert queued.accepted and queued.queued and not queued.delivered

        with JsonCommandInbox("esp32", bus_dir=root) as inbox:
            assert owner_is_active("esp32", root)
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

        assert not owner_is_active("esp32", root)
        with JsonCommandInbox("esp32", bus_dir=root) as recovered:
            replay_after_crash = recovered.drain()
            assert replay_after_crash == [
                {"sequence": 3, "type": "menu_sync"}
            ]
            recovered.acknowledge()

        with JsonCommandInbox("heltec", bus_dir=root) as heltec:
            assert owner_is_active("heltec", root)
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

        oversized_menu = {
            "type": "killerkoala_face",
            "state": "menu_highlight",
            "message": "99/99 " + ("very long selected menu label " * 20),
            "selected_label": "label" * 40,
            "selected_command": "command" * 40,
            "target_display": "heltec-t114",
            "duration_ms": 60000,
            "enabled": True,
        }
        compact_menu = compact_heltec_payload(oversized_menu)
        assert compact_menu["type"] == "killerkoala_face"
        assert "target_display" not in compact_menu
        assert "selected_command" not in compact_menu
        assert wire_length(compact_menu) <= HELTEC_MAX_LINE_BYTES

        compact_speech = compact_heltec_payload(
            {
                "type": "killerkoala_speech",
                "active": True,
                "message": "speech " * 100,
                "target_display": "heltec-t114",
            }
        )
        assert wire_length(compact_speech) <= HELTEC_MAX_LINE_BYTES

        payload = {
            "status": "SERIAL_COMMAND_BUS_READY",
            "single_owner_enforced": True,
            "startup_spool_replayed": True,
            "active_owner_notified": True,
            "offline_nonqueued_command_rejected": True,
            "owner_lock_detection_verified": True,
            "claim_acknowledgement_required": True,
            "crash_replay_verified": True,
            "heltec_wire_limit_bytes": HELTEC_MAX_LINE_BYTES,
            "heltec_compaction_verified": True,
            "targets": ["esp32", "heltec"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
