from __future__ import annotations

import fcntl
import os
from pathlib import Path

from .serial_command_bus import socket_path


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def owner_lock_path(target: str) -> Path:
    socket = socket_path(target)
    return socket.with_name(f"{target}.owner.lock")


def owner_is_active(target: str) -> bool:
    """Check the advisory owner lock rather than trusting socket-file presence."""

    lock_path = owner_lock_path(target)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return False


def direct_serial_maintenance_allowed(
    target: str,
    *,
    env_var: str,
) -> bool:
    return _truthy(os.getenv(env_var, "0")) and not owner_is_active(target)


def require_direct_serial_maintenance(
    target: str,
    *,
    env_var: str,
    service_name: str,
) -> None:
    if not _truthy(os.getenv(env_var, "0")):
        raise RuntimeError(
            f"direct {target} serial access is disabled; use the owner bus or set "
            f"{env_var}=1 for isolated maintenance"
        )
    if owner_is_active(target):
        raise RuntimeError(
            f"the {target} serial owner is still active; stop {service_name} before "
            "using direct maintenance mode"
        )


__all__ = [
    "direct_serial_maintenance_allowed",
    "owner_is_active",
    "owner_lock_path",
    "require_direct_serial_maintenance",
]
