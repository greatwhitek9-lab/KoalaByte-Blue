from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from .bounded_log import append_jsonl


def atomic_write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(
        f".{target.name}.tmp.{os.getpid()}.{time.time_ns()}"
    )
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, target)


def install_runtime_log_hardening() -> None:
    """Patch legacy append-only runtime log helpers with bounded writers."""

    from . import killerkoala_error_dig, killerkoala_face_bridge

    if not getattr(killerkoala_face_bridge, "_bounded_logging_installed", False):
        def write_face_result(filename: str, result: dict[str, Any]) -> None:
            log_dir = killerkoala_face_bridge.DEFAULT_LOG_DIR
            atomic_write_json(log_dir / filename, result)
            append_jsonl(log_dir / "face_commands.jsonl", result)

        killerkoala_face_bridge._write_result_log = write_face_result
        killerkoala_face_bridge._bounded_logging_installed = True

    if not getattr(killerkoala_error_dig, "_bounded_logging_installed", False):
        def save_history(rows: list[str]) -> None:
            atomic_write_json(
                killerkoala_error_dig.ERROR_DIG_HISTORY_PATH,
                {"recent": rows[-12:], "updated_at": time.time()},
            )

        def append_error_event(payload: Mapping[str, Any]) -> None:
            append_jsonl(
                killerkoala_error_dig.ERROR_DIG_EVENT_PATH,
                dict(payload),
            )

        killerkoala_error_dig._save_history = save_history
        killerkoala_error_dig._append_event = append_error_event
        killerkoala_error_dig._bounded_logging_installed = True


__all__ = ["atomic_write_json", "install_runtime_log_hardening"]
