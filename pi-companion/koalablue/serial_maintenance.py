from __future__ import annotations

import os
from pathlib import Path

from .serial_command_bus import owner_is_active, socket_path


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def owner_lock_path(target: str) -> Path:
    socket = socket_path(target)
    return socket.with_name(f"{target}.owner.lock")


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
