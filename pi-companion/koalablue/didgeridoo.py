from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from . import meshtastic_app

ACTION_NAME = "Didgeridoo Meshtastic"
DEFAULT_LOG_DIR = Path("logs/didgeridoo")


@dataclass
class DidgeridooResult:
    action: str
    status: str
    started_at: float
    ended_at: float
    artifact_path: str
    checks: List[Dict[str, Any]]
    note: str


def _safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    profile = redacted.get("profile")
    if isinstance(profile, dict):
        profile = dict(profile)
        for key in ("host", "ble"):
            if profile.get(key):
                profile[key] = "configured"
        redacted["profile"] = profile
    return redacted


def run_once(log_dir: str | Path = DEFAULT_LOG_DIR) -> DidgeridooResult:
    started = time.time()
    root = Path(log_dir)
    root.mkdir(parents=True, exist_ok=True)
    checks: List[Dict[str, Any]] = []

    for name, func in (
        ("status", meshtastic_app.status),
        ("nodes", meshtastic_app.nodes),
        ("gps", meshtastic_app.gps_info),
    ):
        try:
            checks.append({"name": name, "payload": _safe_payload(func())})
        except Exception as exc:
            checks.append({"name": name, "status": "error", "error": str(exc)})

    ended = time.time()
    overall = "success" if any(check.get("payload") for check in checks) else "error"
    artifact = root / f"didgeridoo_meshtastic_{time.strftime('%Y%m%d_%H%M%S', time.localtime(started))}.json"
    result = DidgeridooResult(
        action=ACTION_NAME,
        status=overall,
        started_at=started,
        ended_at=ended,
        artifact_path=str(artifact),
        checks=checks,
        note="Safe Meshtastic status, node table, and GNSS/status bundle only. Didgeridoo does not send messages from the menu action.",
    )
    artifact.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")
    return result


def run_cli() -> int:
    result = run_once()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0 if result.status == "success" else 1
