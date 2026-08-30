#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

SCHEMA = 1

STAGE_ORDER = [
    "source_validation",
    "pi_prerequisites",
    "firmware_deployment",
    "tinyllama",
    "mopidy",
    "power_permissions",
    "runtime_services",
    "device_discovery",
    "gpio_initialization",
    "runtime_verification",
    "service_activation",
    "runtime_health",
    "audio_selection",
    "final_doctor",
    "cleanup",
]
STAGE_SET = set(STAGE_ORDER)


def _now() -> float:
    return time.time()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"cannot read checkpoint {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"checkpoint is not a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _profile(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"invalid profile JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("profile JSON must be an object")
    return value


def _empty_state(profile: dict[str, Any], source_revision: str) -> dict[str, Any]:
    now = _now()
    return {
        "schema": SCHEMA,
        "profile": profile,
        "source_revision_at_create": source_revision,
        "source_revision_last_seen": source_revision,
        "completed": [],
        "completed_at": {},
        "current_stage": None,
        "current_label": None,
        "failed_stage": None,
        "failed_label": None,
        "failure_reason": None,
        "legacy_migration": False,
        "created_at": now,
        "updated_at": now,
    }


def _validate_state(state: dict[str, Any]) -> None:
    if state.get("schema") != SCHEMA:
        raise RuntimeError(
            f"unsupported checkpoint schema {state.get('schema')!r}; expected {SCHEMA}. "
            "Use --reset-progress to start a new checkpoint."
        )
    completed = state.get("completed", [])
    if not isinstance(completed, list) or any(stage not in STAGE_SET for stage in completed):
        raise RuntimeError("checkpoint contains unknown completed stages")


def _check_profile(state: dict[str, Any], profile: dict[str, Any]) -> None:
    previous = state.get("profile")
    if previous != profile:
        old = json.dumps(previous, sort_keys=True)
        new = json.dumps(profile, sort_keys=True)
        raise RuntimeError(
            "resume profile differs from the checkpoint. "
            f"checkpoint={old}; requested={new}. "
            "Use the same deployment options or --reset-progress for a fresh run."
        )


def _read_status(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _legacy_successes(root: Path) -> list[tuple[str, str]]:
    successes: list[tuple[str, str]] = []

    firmware = _read_status(root / "logs/deployment/whole_system_deployment_status.json")
    if str(firmware.get("status", "")).lower() == "complete":
        successes.append(("firmware_deployment", "legacy whole-system firmware status is complete"))

    ollama = _read_status(root / "logs/killerkoala/ollama_setup_status.json")
    if (
        str(ollama.get("status", "")).lower() == "ok"
        and str(ollama.get("step", "")) == "killerkoala_ollama"
    ):
        successes.append(("tinyllama", "legacy KillerKoala Ollama status is ok"))

    mopidy = _read_status(root / "logs/music_player/mopidy_setup_status.json")
    if str(mopidy.get("status", "")) == "MOPIDY_PLAYER_READY":
        successes.append(("mopidy", "legacy Mopidy status is MOPIDY_PLAYER_READY"))

    return successes


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.path)
    profile = _profile(args.profile_json)
    if path.exists():
        state = _load_json(path)
        _validate_state(state)
        _check_profile(state, profile)
    else:
        state = _empty_state(profile, args.source_revision)
    state["source_revision_last_seen"] = args.source_revision
    state["updated_at"] = _now()
    _write_json(path, state)
    return 0


def cmd_migrate_legacy(args: argparse.Namespace) -> int:
    path = Path(args.path)
    profile = _profile(args.profile_json)
    if path.exists():
        state = _load_json(path)
        _validate_state(state)
        _check_profile(state, profile)
        return 0

    state = _empty_state(profile, args.source_revision)
    state["legacy_migration"] = True
    state["legacy_migration_at"] = _now()
    state["legacy_migration_evidence"] = {}
    completed_at = state["completed_at"]
    for stage, reason in _legacy_successes(Path(args.root)):
        if stage not in state["completed"]:
            state["completed"].append(stage)
            completed_at[stage] = _now()
        state["legacy_migration_evidence"][stage] = reason
    state["updated_at"] = _now()
    _write_json(path, state)
    print(json.dumps({
        "checkpoint": str(path),
        "legacy_migration": True,
        "adopted_completed": state["completed"],
        "evidence": state["legacy_migration_evidence"],
    }, indent=2, sort_keys=True))
    return 0


def cmd_is_complete(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        return 1
    state = _load_json(path)
    _validate_state(state)
    return 0 if args.stage in state.get("completed", []) else 1


def _require_stage(stage: str) -> None:
    if stage not in STAGE_SET:
        raise RuntimeError(f"unknown stage: {stage}")


def cmd_started(args: argparse.Namespace) -> int:
    _require_stage(args.stage)
    path = Path(args.path)
    state = _load_json(path)
    _validate_state(state)
    state["current_stage"] = args.stage
    state["current_label"] = args.label
    state["failed_stage"] = None
    state["failed_label"] = None
    state["failure_reason"] = None
    state["updated_at"] = _now()
    _write_json(path, state)
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    _require_stage(args.stage)
    path = Path(args.path)
    state = _load_json(path)
    _validate_state(state)
    completed = state.setdefault("completed", [])
    if args.stage not in completed:
        completed.append(args.stage)
        completed.sort(key=STAGE_ORDER.index)
    state.setdefault("completed_at", {})[args.stage] = _now()
    state["current_stage"] = None
    state["current_label"] = None
    state["failed_stage"] = None
    state["failed_label"] = None
    state["failure_reason"] = None
    state["updated_at"] = _now()
    _write_json(path, state)
    return 0


def cmd_failed(args: argparse.Namespace) -> int:
    _require_stage(args.stage)
    path = Path(args.path)
    if not path.exists():
        return 0
    state = _load_json(path)
    _validate_state(state)
    state["current_stage"] = args.stage
    state["current_label"] = args.label
    state["failed_stage"] = args.stage
    state["failed_label"] = args.label
    state["failure_reason"] = args.reason
    state["updated_at"] = _now()
    _write_json(path, state)
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    path = Path(args.path)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(json.dumps({"checkpoint": str(path), "status": "absent"}, indent=2))
        return 0
    state = _load_json(path)
    _validate_state(state)
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Durable KoalaByte one-shot stage checkpoint helper")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--path", required=True)
    init.add_argument("--profile-json", required=True)
    init.add_argument("--source-revision", default="unknown")
    init.set_defaults(func=cmd_init)

    migrate = sub.add_parser("migrate-legacy")
    migrate.add_argument("--path", required=True)
    migrate.add_argument("--profile-json", required=True)
    migrate.add_argument("--source-revision", default="unknown")
    migrate.add_argument("--root", required=True)
    migrate.set_defaults(func=cmd_migrate_legacy)

    complete = sub.add_parser("is-complete")
    complete.add_argument("--path", required=True)
    complete.add_argument("--stage", required=True, choices=STAGE_ORDER)
    complete.set_defaults(func=cmd_is_complete)

    started = sub.add_parser("started")
    started.add_argument("--path", required=True)
    started.add_argument("--stage", required=True, choices=STAGE_ORDER)
    started.add_argument("--label", required=True)
    started.set_defaults(func=cmd_started)

    done = sub.add_parser("complete")
    done.add_argument("--path", required=True)
    done.add_argument("--stage", required=True, choices=STAGE_ORDER)
    done.set_defaults(func=cmd_complete)

    failed = sub.add_parser("failed")
    failed.add_argument("--path", required=True)
    failed.add_argument("--stage", required=True, choices=STAGE_ORDER)
    failed.add_argument("--label", required=True)
    failed.add_argument("--reason", required=True)
    failed.set_defaults(func=cmd_failed)

    reset = sub.add_parser("reset")
    reset.add_argument("--path", required=True)
    reset.set_defaults(func=cmd_reset)

    show = sub.add_parser("show")
    show.add_argument("--path", required=True)
    show.set_defaults(func=cmd_show)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"checkpoint error: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
