from __future__ import annotations

import fcntl
import json
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


def _queue_path(target: str, bus_dir: str | Path | None = None) -> Path:
    return _root(bus_dir) / f"{_target(target)}.queue.jsonl"


def _queue_lock_path(target: str, bus_dir: str | Path | None = None) -> Path:
    return _root(bus_dir) / f"{_target(target)}.queue.lock"


def _encode(payload: dict[str, Any]) -> bytes:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(data) > MAX_DATAGRAM_BYTES:
        raise ValueError(
            f"serial command is {len(data)} bytes; limit is {MAX_DATAGRAM_BYTES}"
        )
    return data


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
        temp = queue_path.with_name(
            f".{queue_path.name}.tmp.{os.getpid()}.{time.time_ns()}"
        )
        temp.write_text("\n".join([*existing, line]) + "\n", encoding="utf-8")
        os.replace(temp, queue_path)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def submit_command(
    target: str,
    payload: dict[str, Any],
    *,
    queue_if_unavailable: bool = True,
    bus_dir: str | Path | None = None,
) -> CommandSubmission:
    resolved_target = _target(target)
    data = _encode(payload)
    destination = socket_path(resolved_target, bus_dir)
    client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        client.sendto(data, str(destination))
        return CommandSubmission(
            True, True, False, resolved_target, "delivered_to_owner"
        )
    except OSError as exc:
        if not queue_if_unavailable:
            return CommandSubmission(
                False,
                False,
                False,
                resolved_target,
                f"owner_unavailable:{exc}",
            )
        try:
            _bounded_queue_append(
                resolved_target,
                payload,
                bus_dir=bus_dir,
            )
            return CommandSubmission(
                True,
                False,
                True,
                resolved_target,
                "queued_for_owner",
            )
        except Exception as queue_exc:
            return CommandSubmission(
                False,
                False,
                False,
                resolved_target,
                f"queue_failed:{queue_exc}",
            )
    finally:
        client.close()


class JsonCommandInbox:
    """Exclusive local command inbox for the process that owns one serial port."""

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
            self.path.unlink(missing_ok=True)
            fcntl.flock(self._owner_lock.fileno(), fcntl.LOCK_UN)
            self._owner_lock.close()
            raise

    def _take_spooled(self) -> list[dict[str, Any]]:
        queue_path = _queue_path(self.target, self.bus_dir)
        lock_path = _queue_lock_path(self.target, self.bus_dir)
        processing: Path | None = None
        with lock_path.open("a+") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            if queue_path.exists():
                processing = queue_path.with_name(
                    f".{queue_path.name}.drain.{os.getpid()}.{time.time_ns()}"
                )
                os.replace(queue_path, processing)
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        if processing is None:
            return []

        commands: list[dict[str, Any]] = []
        try:
            for line in processing.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines():
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    commands.append(payload)
        finally:
            processing.unlink(missing_ok=True)
        return commands

    def drain(self, *, max_items: int = 64) -> list[dict[str, Any]]:
        if self._closed or self._socket is None:
            return []
        limit = max(0, int(max_items))
        commands = self._take_spooled()
        while len(commands) < limit:
            try:
                data = self._socket.recv(MAX_DATAGRAM_BYTES)
            except BlockingIOError:
                break
            except OSError:
                break
            try:
                payload = json.loads(data.decode("utf-8", errors="ignore"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and not payload.get("_bus_probe"):
                commands.append(payload)
        if len(commands) <= limit:
            return commands
        overflow = commands[limit:]
        for payload in overflow:
            _bounded_queue_append(self.target, payload, bus_dir=self.bus_dir)
        return commands[:limit]

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
            fcntl.flock(self._owner_lock.fileno(), fcntl.LOCK_UN)
            self._owner_lock.close()

    def __enter__(self) -> "JsonCommandInbox":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def drain_to_writer(
    inbox: JsonCommandInbox,
    writer: Any,
    *,
    max_items: int = 64,
) -> int:
    written = 0
    for payload in inbox.drain(max_items=max_items):
        writer(payload)
        written += 1
    return written


__all__ = [
    "CommandSubmission",
    "JsonCommandInbox",
    "drain_to_writer",
    "socket_path",
    "submit_command",
]
