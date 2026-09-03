#!/usr/bin/env python3
from __future__ import annotations

from koalablue import eucalyptus_persistent_worker as worker
from koalablue import eucalyptus_wigle


def main() -> int:
    control = eucalyptus_wigle.control_status
    if not getattr(control, "_koalabyte_persistent_worker", False):
        raise SystemExit("Eucalyptus control_status is not patched for persistent worker control")

    original_start = worker.start_worker
    original_stop = worker.stop_worker
    original_restart = worker.restart_worker
    try:
        worker.start_worker = lambda: {"status": "TEST_STARTED", "active": True}  # type: ignore[assignment]
        worker.stop_worker = lambda timeout_seconds=5.0: {"status": "TEST_STOPPED", "active": False}  # type: ignore[assignment]
        worker.restart_worker = lambda: {"status": "TEST_RESTARTED", "active": True}  # type: ignore[assignment]

        started = control("start")
        stopped = control("stop")
        restarted = control("restart")

        assert started.get("status") == "TEST_STARTED" and started.get("active") is True
        assert stopped.get("status") == "TEST_STOPPED" and stopped.get("active") is False
        assert restarted.get("status") == "TEST_RESTARTED" and restarted.get("active") is True
    finally:
        worker.start_worker = original_start  # type: ignore[assignment]
        worker.stop_worker = original_stop  # type: ignore[assignment]
        worker.restart_worker = original_restart  # type: ignore[assignment]

    print("Eucalyptus persistent worker routing check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
