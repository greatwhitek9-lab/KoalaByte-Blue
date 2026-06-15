from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_STATE_PATH = Path("logs/dongle_mode_state.json")
DEFAULT_EVENT_LOG = Path("logs/dongle_mode_events.jsonl")
DEFAULT_ACTIVE_MODE = "koalabyte_lab"


@dataclass(frozen=True)
class DongleModeSpec:
    key: str
    title: str
    build_script: str
    package_script: str
    build_dir: str
    hex_path: str
    dfu_zip: str
    host_note: str
    killerkoala_loaded_line: str


@dataclass
class StepResult:
    command: List[str]
    returncode: int
    stdout: str
    stderr: str


MODES: Dict[str, DongleModeSpec] = {
    "koalabyte_lab": DongleModeSpec(
        "koalabyte_lab",
        "KoalaByte Lab",
        "scripts/build_nrf52840_dongle_lab.sh",
        "scripts/flash_nrf52840_dongle_lab_dfu.sh",
        "build/nrf52840-dongle-lab",
        "build/nrf52840-dongle-lab/zephyr/zephyr.hex",
        "build/nrf52840-dongle-lab/koalabyte-blue-nrf52840-dongle-dfu.zip",
        "Dongle advertises as KoalaByte Lab for owned-device BLE scan testing.",
        "KoalaByte Lab loaded. Clean beacon, clean scope, and the lab signal is ours.",
    ),
    "koala_konnect": DongleModeSpec(
        "koala_konnect",
        "Koala Konnect",
        "scripts/build_koala_konnect.sh",
        "scripts/flash_koala_konnect.sh",
        "build/nrf52840-dongle-koala-konnect",
        "build/nrf52840-dongle-koala-konnect/zephyr/zephyr.hex",
        "build/nrf52840-dongle-koala-konnect/koala-konnect-nrf52840-dongle-dfu.zip",
        "Replug the dongle into the phone or computer host USB port.",
        "Koala Konnect loaded. Plug me into the host and let the machine drive the stack.",
    ),
}

ALIASES = {
    "lab": "koalabyte_lab",
    "koalabyte lab": "koalabyte_lab",
    "koalabyte_lab": "koalabyte_lab",
    "koala lab": "koalabyte_lab",
    "konnect": "koala_konnect",
    "koala konnect": "koala_konnect",
    "koala_konnect": "koala_konnect",
    "adapter": "koala_konnect",
    "external adapter": "koala_konnect",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_mode(name: str) -> DongleModeSpec:
    normalized = name.strip().lower().replace("-", " ").replace("_", " ")
    key = ALIASES.get(normalized, normalized.replace(" ", "_"))
    if key not in MODES:
        raise ValueError(f"Unknown dongle mode: {name}. Use koalabyte_lab or koala_konnect.")
    return MODES[key]


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def artifact_status(root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    root = root or repo_root()
    out: Dict[str, Dict[str, Any]] = {}
    for key, spec in MODES.items():
        out[key] = {
            "title": spec.title,
            "build_dir": spec.build_dir,
            "hex_path": spec.hex_path,
            "dfu_zip": spec.dfu_zip,
            "build_dir_exists": (root / spec.build_dir).exists(),
            "hex_exists": (root / spec.hex_path).exists(),
            "dfu_zip_exists": (root / spec.dfu_zip).exists(),
        }
    return out


def load_state(path: Path = DEFAULT_STATE_PATH) -> Dict[str, Any]:
    if not path.exists():
        default = MODES[DEFAULT_ACTIVE_MODE]
        return {
            "active_mode": DEFAULT_ACTIVE_MODE,
            "active_title": default.title,
            "default_mode": DEFAULT_ACTIVE_MODE,
            "default_title": default.title,
            "killerkoala_line": default.killerkoala_loaded_line,
            "last_action": "default",
            "updated_at": time.time(),
            "note": "Default production/lab mode is KoalaByte Lab until Koala Konnect is flashed.",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(payload: Dict[str, Any], path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def append_event(payload: Dict[str, Any], path: Path = DEFAULT_EVENT_LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_jsonable(payload), sort_keys=True) + "\n")


def run_step(command: List[str], *, root: Path, env_extra: Optional[Dict[str, str]] = None) -> StepResult:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    done = subprocess.run(command, cwd=root, text=True, capture_output=True, env=env)
    return StepResult(command, done.returncode, done.stdout, done.stderr)


def finish(action: str, mode: Optional[DongleModeSpec], status: str, message: str, steps: List[StepResult], active_mode: Optional[str] = None, error: Optional[str] = None, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG) -> Dict[str, Any]:
    root = repo_root()
    previous = load_state(state_path)
    mode_key = active_mode or str(previous.get("active_mode", DEFAULT_ACTIVE_MODE))
    title = MODES[mode_key].title if mode_key in MODES else str(previous.get("active_title", "Unknown"))
    killerkoala_line = MODES[mode_key].killerkoala_loaded_line if mode_key in MODES else "Koala mode state is unknown. Check the dongle before testing."
    payload = {
        "action": action,
        "requested_mode": mode.key if mode else None,
        "requested_title": mode.title if mode else None,
        "status": status,
        "message": message,
        "error": error,
        "active_mode": mode_key,
        "active_title": title,
        "default_mode": DEFAULT_ACTIVE_MODE,
        "default_title": MODES[DEFAULT_ACTIVE_MODE].title,
        "killerkoala_line": killerkoala_line,
        "updated_at": time.time(),
        "state_path": str(state_path),
        "event_log": str(event_log),
        "artifacts": artifact_status(root),
        "steps": steps,
        "safety": {
            "default_production_lab_mode": MODES[DEFAULT_ACTIVE_MODE].title,
            "single_firmware_installed_at_a_time": True,
            "dfu_flash_requires_explicit_port": True,
            "authorized_lab_use_only": True,
        },
    }
    write_state(payload, state_path)
    append_event(payload, event_log)
    return payload


def status(state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG) -> Dict[str, Any]:
    state = load_state(state_path)
    active = str(state.get("active_mode", DEFAULT_ACTIVE_MODE))
    return finish("status", None, "success", "Koala Mode Switcher status written.", [], active_mode=active, state_path=state_path, event_log=event_log)


def build(mode_name: str, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG) -> Dict[str, Any]:
    root = repo_root()
    mode = resolve_mode(mode_name)
    step = run_step(["bash", mode.build_script], root=root)
    if step.returncode != 0:
        return finish("build", mode, "error", f"{mode.title} build failed.", [step], error=step.stderr or step.stdout, state_path=state_path, event_log=event_log)
    return finish("build", mode, "success", f"{mode.title} build complete.", [step], state_path=state_path, event_log=event_log)


def package(mode_name: str, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG) -> Dict[str, Any]:
    root = repo_root()
    mode = resolve_mode(mode_name)
    step = run_step(["bash", mode.package_script], root=root, env_extra={"NRF_DFU_PORT": ""})
    if step.returncode != 0:
        return finish("package", mode, "error", f"{mode.title} DFU package failed.", [step], error=step.stderr or step.stdout, state_path=state_path, event_log=event_log)
    return finish("package", mode, "success", f"{mode.title} DFU package ready.", [step], state_path=state_path, event_log=event_log)


def prepare(mode_name: str, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG) -> Dict[str, Any]:
    mode = resolve_mode(mode_name)
    root = repo_root()
    steps: List[StepResult] = []
    first = run_step(["bash", mode.build_script], root=root)
    steps.append(first)
    if first.returncode != 0:
        return finish("prepare", mode, "error", f"{mode.title} prepare failed during build.", steps, error=first.stderr or first.stdout, state_path=state_path, event_log=event_log)
    second = run_step(["bash", mode.package_script], root=root, env_extra={"NRF_DFU_PORT": ""})
    steps.append(second)
    if second.returncode != 0:
        return finish("prepare", mode, "error", f"{mode.title} prepare failed during DFU package creation.", steps, error=second.stderr or second.stdout, state_path=state_path, event_log=event_log)
    return finish("prepare", mode, "success", f"{mode.title} build and DFU package ready.", steps, state_path=state_path, event_log=event_log)


def prepare_all(state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG) -> Dict[str, Any]:
    root = repo_root()
    steps: List[StepResult] = []
    for mode in MODES.values():
        first = run_step(["bash", mode.build_script], root=root)
        steps.append(first)
        if first.returncode != 0:
            return finish("prepare-all", mode, "error", f"Prepare all failed while building {mode.title}.", steps, error=first.stderr or first.stdout, state_path=state_path, event_log=event_log)
        second = run_step(["bash", mode.package_script], root=root, env_extra={"NRF_DFU_PORT": ""})
        steps.append(second)
        if second.returncode != 0:
            return finish("prepare-all", mode, "error", f"Prepare all failed while packaging {mode.title}.", steps, error=second.stderr or second.stdout, state_path=state_path, event_log=event_log)
    return finish("prepare-all", None, "success", "Both firmwares built and both DFU ZIPs created.", steps, state_path=state_path, event_log=event_log)


def apply_mode(mode_name: str, dfu_port: str, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG) -> Dict[str, Any]:
    mode = resolve_mode(mode_name)
    if not dfu_port.strip():
        return finish("switch", mode, "blocked", "DFU port required. Use --dfu-port /dev/ttyACM0 or NRF_DFU_PORT.", [], error="missing DFU port", state_path=state_path, event_log=event_log)
    root = repo_root()
    step = run_step(["bash", mode.package_script], root=root, env_extra={"NRF_DFU_PORT": dfu_port.strip()})
    if step.returncode != 0:
        return finish("switch", mode, "error", f"{mode.title} DFU switch failed.", [step], error=step.stderr or step.stdout, state_path=state_path, event_log=event_log)
    return finish("switch", mode, "success", f"{mode.title} is now selected. {mode.host_note}", [step], active_mode=mode.key, state_path=state_path, event_log=event_log)


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="Koala Mode Switcher for the nRF52840 Dongle")
    parser.add_argument("action", choices=["status", "build", "package", "prepare", "prepare-all", "apply", "switch"])
    parser.add_argument("mode", nargs="?", default=None, help="koalabyte_lab or koala_konnect")
    parser.add_argument("--dfu-port", default=os.environ.get("NRF_DFU_PORT", ""))
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--event-log", default=str(DEFAULT_EVENT_LOG))
    args = parser.parse_args()

    state_path = Path(args.state_path)
    event_log = Path(args.event_log)
    try:
        if args.action == "status":
            result = status(state_path, event_log)
        elif args.action == "prepare-all":
            result = prepare_all(state_path, event_log)
        else:
            if not args.mode:
                parser.error(f"{args.action} requires a mode")
            if args.action == "build":
                result = build(args.mode, state_path, event_log)
            elif args.action == "package":
                result = package(args.mode, state_path, event_log)
            elif args.action == "prepare":
                result = prepare(args.mode, state_path, event_log)
            elif args.action in {"apply", "switch"}:
                result = apply_mode(args.mode, args.dfu_port, state_path, event_log)
            else:
                raise ValueError(args.action)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
