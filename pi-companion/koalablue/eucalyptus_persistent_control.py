from __future__ import annotations

from typing import Any


def install_eucalyptus_persistent_control() -> None:
    """Patch Eucalyptus START/STOP/RESTART without importing the worker at package import.

    Keeping the worker import lazy avoids the runpy warning when operators invoke
    ``python -m koalablue.eucalyptus_persistent_worker`` directly.
    """

    from . import eucalyptus_wigle

    original = eucalyptus_wigle.control_status
    if getattr(original, "_koalabyte_persistent_worker", False):
        return

    def control_status(action: str) -> dict[str, Any]:
        normalized = str(action or "status").strip().lower()
        if normalized in {"start", "stop", "restart"}:
            from . import eucalyptus_persistent_worker as worker

            if normalized == "start":
                return worker.start_worker()
            if normalized == "stop":
                return worker.stop_worker()
            return worker.restart_worker()

        result = original(action)
        if normalized == "status" and isinstance(result, dict):
            from .eucalyptus_persistent_worker import worker_status

            result = dict(result)
            result["persistent_worker"] = worker_status()
        return result

    control_status._koalabyte_persistent_worker = True  # type: ignore[attr-defined]
    eucalyptus_wigle.control_status = control_status


__all__ = ["install_eucalyptus_persistent_control"]
