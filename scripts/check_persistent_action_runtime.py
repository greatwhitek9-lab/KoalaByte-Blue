#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="koalabyte-persistent-actions-") as temp:
        os.chdir(temp)

        from koalablue.persistent_action_state import (
            action_key,
            active_actions,
            apply_lifecycle_transition,
            lifecycle_intent,
        )

        cases = {
            "eucalyptus start": "start",
            "eucalyptus stop": "stop",
            "eucalyptus restart": "restart",
            "eucalyptus_gps_on": "start",
            "eucalyptus_gps_off": "stop",
            "lab_transmit_bench_arm_on": "start",
            "lab_transmit_bench_arm_off": "stop",
            "meshtastic_confirm_send_on": "start",
            "meshtastic_confirm_send_off": "stop",
            "koala_bluez_scan": None,
            "t114_primary_ble_scan": None,
            "power_on_off": None,
            "status": None,
        }
        for command, expected in cases.items():
            actual = lifecycle_intent(command, command)
            if actual != expected:
                failures.append(f"{command!r}: expected {expected!r}, got {actual!r}")

        if action_key("eucalyptus start") != action_key("eucalyptus stop"):
            failures.append("Eucalyptus start/stop do not share an action key")
        if action_key("eucalyptus_gps_on") != action_key("eucalyptus_gps_off"):
            failures.append("Eucalyptus GPS on/off do not share an action key")

        started = apply_lifecycle_transition(
            "eucalyptus start",
            "Eucalyptus Canopy Start",
            {"status": "SUCCESS"},
            source="regression",
        )
        if not started or not started.get("active"):
            failures.append("successful START did not become active")
        if "eucalyptus" not in active_actions():
            failures.append("active action registry did not contain eucalyptus")

        failed_stop = apply_lifecycle_transition(
            "eucalyptus stop",
            "Eucalyptus Canopy Stop",
            {"status": "FAILED", "error": "simulated"},
            source="regression",
        )
        if not failed_stop or not failed_stop.get("active"):
            failures.append("failed STOP incorrectly cleared active state")

        stopped = apply_lifecycle_transition(
            "eucalyptus stop",
            "Eucalyptus Canopy Stop",
            {"status": "SUCCESS"},
            source="regression",
        )
        if not stopped or stopped.get("active"):
            failures.append("successful STOP did not clear active state")
        if "eucalyptus" in active_actions():
            failures.append("stopped action remained in active action registry")

        restarted = apply_lifecycle_transition(
            "eucalyptus restart",
            "Eucalyptus Canopy Restart",
            {"status": "SUCCESS"},
            source="regression",
        )
        if not restarted or not restarted.get("active"):
            failures.append("RESTART did not return action to active state")

        from koalablue.persistent_action_runtime import install_persistent_action_runtime
        from koalablue.killerkoala_face_bridge import KOALAGOTCHI_DISPLAY_COMMANDS

        install_persistent_action_runtime()
        if "eucalyptus start" not in KOALAGOTCHI_DISPLAY_COMMANDS:
            failures.append("voice persistence set missing eucalyptus start")
        if "eucalyptus stop" in KOALAGOTCHI_DISPLAY_COMMANDS:
            failures.append("voice persistence set incorrectly includes eucalyptus stop")

        state_path = Path("logs/runtime/persistent_actions.json")
        if not state_path.is_file():
            failures.append("persistent action state file was not written")

    if failures:
        print("Persistent action runtime check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Persistent action runtime check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
