from __future__ import annotations

import fcntl
import json
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

DEFAULT_BUS_DIR = Path(
    os.getenv("KOALABYTE_SERIAL_BUS_DIR", "logs/runtime/serial_bus")
)
MAX_DATAGRAM_BYTES = max(
    1024, int(os.getenv("KOALABYTE_SERIAL_BUS_MAX_BYTES", "32768"))
)
MAX_QUEUED_COMMANDS = max(
    1, int(os.getenv("KOALABYTE_SERIAL_BUS_MAX_QUEUE", "256"))
)
VALID_TARGETS = {"esp32", "heltec"}
_WAKE = b"K"


@dataclass(frozen=True)
class CommandSubmission:
    accepted: bool
    delivered: bool
    queued: bool
    target: str
    status: str


def _target(value: str) -> str:
    target = str(value or "").strip().lower()
    if target not in VALID_TARGETS:
        raise ValueError(f"unsupported serial-command target: {value!r}")
    return target


def _root(bus_dir: str | Path | None = None) -> Path:
    root = Path(bus_dir) if bus_dir is not None else DEFAULT_BUS_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def socket_path(target: str, bus_dir: str | Path | None = None) -> Path:
    return _root(bus_dir) / f"{_target(target)}.sock"


def _owner_lock_path(target: str, bus_dir: str | Path | None = None) -> Path:
    return _root(bus_dir) / f"{_target(target)}.owner.lock"


def owner_is_active(
    target: str,
    bus_dir: str | Path | None = None,
) -> bool:
    """Return whether another process currently holds the target owner lock."""

    lock_path = _owner_lock_path(target, bus_dir)
    with lock_path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return False


def _queue_path(target: str, bus_dir: str | Path | None = None) -> Path:
    return _root(bus_dir) / f"{_target(target)}.queue.jsonl"


def _queue_lock_path(target: str, bus_dir: str | Path | None = None) -> Path:
    return _root(bus_dir) / f"{_target(target)}.queue.lock"


def _claim_pattern(target: str) -> str:
    return f".{_target(target)}.queue.claim.*.jsonl"


def _encode(payload: dict[str, Any]) -> bytes:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(data) > MAX_DATAGRAM_BYTES:
        raise ValueError(
            f"serial command is {len(data)} bytes; limit is {MAX_DATAGRAM_BYTES}"
        )
    return data


def _atomic_write_lines(path: Path, lines: list[str]) -> None:
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    temp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    os.replace(temp, path)


def _bounded_queue_append(
    target: str,
    payload: dict[str, Any],
    *,
    bus_dir: str | Path | None = None,
) -> None:
    queue_path = _queue_path(target, bus_dir)
    lock_path = _queue_lock_path(target, bus_dir)
    line = _encode(payload).decode("utf-8")
    with lock_path.open("a+") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        existing: list[str] = []
        if queue_path.exists():
            existing = [
                row
                for row in queue_path.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines()
                if row.strip()
            ]
        keep = MAX_QUEUED_COMMANDS - 1
        existing = existing[-keep:] if keep > 0 else []
        _atomic_write_lines(queue_path, [*existing, line])
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def submit_command(
    target: str,
    payload: dict[str, Any],
    *,
    queue_if_unavailable: bool = True,
    bus_dir: str | Path | None = None,
) -> CommandSubmission:
    """Persist a command and wake the exclusive serial owner.

    When ``queue_if_unavailable`` is true, the command is durably spooled even
    when the owner is offline. When false, an offline owner rejects the command
    before it is persisted. If the owner exits after the lock check but before
    notification, the already-persisted command remains queued rather than being
    silently lost.
    """

    resolved_target = _target(target)
    if not queue_if_unavailable and not owner_is_active(
        resolved_target, bus_dir
    ):
        return CommandSubmission(
            False,
            False,
            False,
            resolved_target,
            "owner_unavailable_not_queued",
        )

    try:
        _bounded_queue_append(resolved_target, dict(payload), bus_dir=bus_dir)
    except Exception as exc:
        return CommandSubmission(
            False,
            False,
            False,
            resolved_target,
            f"queue_failed:{exc}",
        )

    destination = socket_path(resolved_target, bus_dir)
    client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        client.sendto(_WAKE, str(destination))
        return CommandSubmission(
            True, True, False, resolved_target, "owner_notified_command_persisted"
        )
    except OSError as exc:
        status = (
            "queued_for_owner"
            if queue_if_unavailable
            else f"owner_raced_command_persisted:{exc}"
        )
        return CommandSubmission(
            True,
            False,
            True,
            resolved_target,
            status,
        )
    finally:
        client.close()


class JsonCommandInbox:
    """Exclusive, crash-resilient command inbox for one serial-port owner."""

    def __init__(
        self,
        target: str,
        *,
        bus_dir: str | Path | None = None,
    ) -> None:
        self.target = _target(target)
        self.bus_dir = _root(bus_dir)
        self.path = socket_path(self.target, self.bus_dir)
        self._owner_lock = _owner_lock_path(self.target, self.bus_dir).open("a+")
        self._socket: socket.socket | None = None
        self._claimed_path: Path | None = None
        self._closed = True
        try:
            fcntl.flock(
                self._owner_lock.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError as exc:
            self._owner_lock.close()
            raise RuntimeError(
                f"another process already owns the {self.target} serial command bus"
            ) from exc

        try:
            # Holding the exclusive owner lock proves any existing socket is stale.
            self.path.unlink(missing_ok=True)
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self._socket.bind(str(self.path))
            self._socket.setblocking(False)
            os.chmod(self.path, 0o660)
            self._closed = False
        except Exception:
            if self._socket is not None:
                self._socket.close()
                self._socket = None
            self.path.unlink(missing_ok=True)
            fcntl.flock(self._owner_lock.fileno(), fcntl.LOCK_UN)
            self._owner_lock.close()
            raise

    def _drain_wake_notifications(self) -> None:
        if self._socket is None:
            return
        while True:
            try:
                self._socket.recv(MAX_DATAGRAM_BYTES)
            except BlockingIOError:
                return
            except OSError:
                return

    def _claim_next(self, max_items: int) -> Path | None:
        if self._claimed_path is not None and self._claimed_path.exists():
            return self._claimed_path

        queue_path = _queue_path(self.target, self.bus_dir)
        lock_path = _queue_lock_path(self.target, self.bus_dir)
        with lock_path.open("a+") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

            # A claim left by a dead owner is replayed before newer commands.
            stale_claims = sorted(
                self.bus_dir.glob(_claim_pattern(self.target)),
                key=lambda path: (path.stat().st_mtime_ns, path.name),
            )
            if stale_claims:
                self._claimed_path = stale_claims[0]
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                return self._claimed_path

            if not queue_path.exists():
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                return None

            lines = [
                row
                for row in queue_path.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines()
                if row.strip()
            ]
            if not lines:
                queue_path.unlink(missing_ok=True)
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                return None

            take = max(1, min(int(max_items), MAX_QUEUED_COMMANDS))
            claimed_lines = lines[:take]
            remaining = lines[take:]
            claim = self.bus_dir / (
                f".{self.target}.queue.claim.{time.time_ns()}.{os.getpid()}.jsonl"
            )
            _atomic_write_lines(claim, claimed_lines)
            if remaining:
                _atomic_write_lines(queue_path, remaining)
            else:
                queue_path.unlink(missing_ok=True)
            self._claimed_path = claim
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            return claim

    def drain(self, *, max_items: int = 64) -> list[dict[str, Any]]:
        if self._closed:
            return []
        self._drain_wake_notifications()
        claim = self._claim_next(max_items)
        if claim is None:
            return []

        commands: list[dict[str, Any]] = []
        for line in claim.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                commands.append(payload)
        return commands

    def acknowledge(self) -> None:
        """Delete the active claim only after every command was written."""

        claim = self._claimed_path
        if claim is not None:
            claim.unlink(missing_ok=True)
        self._claimed_path = None

    def drain_to_writer(
        self,
        writer: Callable[[dict[str, Any]], Any],
        *,
        max_items: int = 64,
    ) -> int:
        commands = self.drain(max_items=max_items)
        if not commands:
            # A claim containing only malformed lines must not block the queue.
            if self._claimed_path is not None:
                self.acknowledge()
            return 0
        written = 0
        for payload in commands:
            writer(payload)
            written += 1
        self.acknowledge()
        return written

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._socket is not None:
                self._socket.close()
                self._socket = None
        finally:
            self.path.unlink(missing_ok=True)
            # Unacknowledged claims intentionally remain for the next owner.
            fcntl.flock(self._owner_lock.fileno(), fcntl.LOCK_UN)
            self._owner_lock.close()

    def __enter__(self) -> "JsonCommandInbox":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


__all__ = [
    "CommandSubmission",
    "JsonCommandInbox",
    "owner_is_active",
    "socket_path",
    "submit_command",
]
