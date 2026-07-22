from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = max(
    65536, int(os.getenv("KOALABYTE_LOG_MAX_BYTES", str(8 * 1024 * 1024)))
)
DEFAULT_BACKUPS = max(1, int(os.getenv("KOALABYTE_LOG_BACKUPS", "3")))


def _rotate(path: Path, backups: int) -> None:
    oldest = path.with_name(f"{path.name}.{backups}")
    oldest.unlink(missing_ok=True)
    for index in range(backups - 1, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        if source.exists():
            os.replace(source, path.with_name(f"{path.name}.{index + 1}"))
    if path.exists():
        os.replace(path, path.with_name(f"{path.name}.1"))


def append_text(
    path: str | Path,
    text: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backups: int = DEFAULT_BACKUPS,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = text.encode("utf-8")
    limit = max(65536, int(max_bytes))
    retained = max(1, int(backups))
    lock_path = target.with_name(f".{target.name}.lock")
    with lock_path.open("a+") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        current_size = target.stat().st_size if target.exists() else 0
        if current_size and current_size + len(encoded) > limit:
            _rotate(target, retained)
        with target.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def append_jsonl(
    path: str | Path,
    payload: dict[str, Any],
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backups: int = DEFAULT_BACKUPS,
) -> None:
    append_text(
        path,
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        max_bytes=max_bytes,
        backups=backups,
    )


__all__ = ["append_jsonl", "append_text"]
