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
DEFAULT_CACHE_PATH = Path("logs/dongle_firmware_cache.json")
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
        "KoalaByte Blue Lab Mode",
        "scripts/build_nrf52840_dongle_lab.sh",
        "scripts/flash_nrf52840_dongle_lab_dfu.sh",
        "build/nrf52840-dongle-lab",
        "build/nrf52840-dongle-lab/zephyr/zephyr.hex",
        "build/nrf52840-dongle-lab/koalabyte-blue-nrf52840-dongle-dfu.zip",
        "Dongle advertises as KoalaByte Lab for owned-device BLE scan testing.",
        "KoalaByte Blue Lab Mode loaded. Clean beacon, clean scope, and the lab signal is ours.",
    ),
    "koala_konnect": DongleModeSpec(
        "koala_konnect",
        "Koala Konnect Mode",
        "scripts/build_koala_konnect.sh",
        "scripts/flash_koala_konnect.sh",
        "build/nrf52840-dongle-koala-konnect",
        "build/nrf52840-dongle-koala-konnect/zephyr/zephyr.hex",
        "build/nrf52840-dongle-koala-konnect/koala-konnect-nrf52840-dongle-dfu.zip",
        "Replug the dongle into the phone or computer host USB port.",
        "Koala Konnect Mode loaded. Plug me into the host and let the machine drive the stack.",
    ),
}

ALIASES = {
    "lab": "koalabyte_lab",
    "koalabyte lab": "koalabyte_lab",
    "koalabyte blue lab": "koalabyte_lab",
    "koalabye blue lab": "koalabyte_lab",
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


def _file_info(path: Path) -> Dict[str, Any]:
    exists = path.exists()
    info: Dict[str, Any] = {"path": str(path), "exists": exists}
    if exists:
        stat = path.stat()
        info.update({"size_bytes": stat.st_size, "mtime": stat.st_mtime})
    return info


def artifact_status(root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    root = root or repo_root()
    out: Dict[str, Dict[str, Any]] = {}
    for key, spec in MODES.items():
        build_dir = root / spec.build_dir
        hex_path = root / spec.hex_path
        dfu_zip = root / spec.dfu_zip
        hex_info = _file_info(hex_path)
        zip_info = _file_info(dfu_zip)
        out[key] = {
            "title": spec.title,
            "build_dir": spec.build_dir,
            "hex_path": spec.hex_path,
            "dfu_zip": spec.dfu_zip,
            "build_dir_exists": build_dir.exists(),
            "hex_exists": bool(hex_info["exists"]),
            "dfu_zip_exists": bool(zip_info["exists"]),
            "flash_ready_from_cache": bool(zip_info["exists"]),
            "hex": hex_info,
            "zip": zip_info,
        }
    return out


def cache_payload(action: str = "cache-status", cache_path: Path = DEFAULT_CACHE_PATH, state_path: Path = DEFAULT_STATE_PATH) -> Dict[str, Any]:
    artifacts = artifact_status(repo_root())
    all_ready = all(bool(mode_status.get("flash_ready_from_cache")) for mode_status in artifacts.values())
    current_state = load_state(state_path)
    payload = {
        "action": action,
        "status": "success",
        "all_modes_flash_ready_from_cache": all_ready,
        "cache_path": str(cache_path),
        "active_mode": current_state.get("active_mode", DEFAULT_ACTIVE_MODE),
        "active_title": current_state.get("active_title", MODES[DEFAULT_ACTIVE_MODE].title),
        "modes": artifacts,
        "required_cache_files": {key: spec.dfu_zip for key, spec in MODES.items()},
        "next_step_if_missing": "Run: PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare-cache",
        "updated_at": time.time(),
        "note": "The Raspberry Pi can flash the nRF52840 Dongle from these cached DFU ZIPs when the dongle is in DFU bootloader mode and NRF_DFU_PORT is set.",
    }
    return payload


def write_firmware_cache(action: str = "cache-status", cache_path: Path = DEFAULT_CACHE_PATH, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG) -> Dict[str, Any]:
    payload = cache_payload(action=action, cache_path=cache_path, state_path=state_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")
    append_event(payload, event_log)
    return payload


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
            "note": "Default production/lab mode is KoalaByte Blue Lab Mode until Koala Konnect Mode is flashed.",
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
    try:
        done = subprocess.run(command, cwd=root, text=True, capture_output=True, env=env)
        return StepResult(command, done.returncode, done.stdout, done.stderr)
    except FileNotFoundError as exc:
        return StepResult(command, 127, "", str(exc))


def finish(action: str, mode: Optional[DongleModeSpec], status: str, message: str, steps: List[StepResult], active_mode: Optional[str] = None, error: Optional[str] = None, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG, cache_path: Path = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
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
        "firmware_cache_path": str(cache_path),
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


def status(state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG, cache_path: Path = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
    state = load_state(state_path)
    active = str(state.get("active_mode", DEFAULT_ACTIVE_MODE))
    result = finish("status", None, "success", "Koala Mode Switcher status written.", [], active_mode=active, state_path=state_path, event_log=event_log, cache_path=cache_path)
    result["firmware_cache"] = cache_payload(cache_path=cache_path, state_path=state_path)
    write_state(result, state_path)
    return result


def build(mode_name: str, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG, cache_path: Path = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
    root = repo_root()
    mode = resolve_mode(mode_name)
    step = run_step(["bash", mode.build_script], root=root)
    if step.returncode != 0:
        return finish("build", mode, "error", f"{mode.title} build failed.", [step], error=step.stderr or step.stdout, state_path=state_path, event_log=event_log, cache_path=cache_path)
    result = finish("build", mode, "success", f"{mode.title} build complete.", [step], state_path=state_path, event_log=event_log, cache_path=cache_path)
    result["firmware_cache"] = write_firmware_cache("build", cache_path, state_path, event_log)
    write_state(result, state_path)
    return result


def package(mode_name: str, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG, cache_path: Path = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
    root = repo_root()
    mode = resolve_mode(mode_name)
    step = run_step(["bash", mode.package_script], root=root, env_extra={"NRF_DFU_PORT": ""})
    if step.returncode != 0:
        return finish("package", mode, "error", f"{mode.title} DFU package failed.", [step], error=step.stderr or step.stdout, state_path=state_path, event_log=event_log, cache_path=cache_path)
    result = finish("package", mode, "success", f"{mode.title} DFU package ready.", [step], state_path=state_path, event_log=event_log, cache_path=cache_path)
    result["firmware_cache"] = write_firmware_cache("package", cache_path, state_path, event_log)
    write_state(result, state_path)
    return result


def prepare(mode_name: str, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG, cache_path: Path = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
    mode = resolve_mode(mode_name)
    root = repo_root()
    steps: List[StepResult] = []
    first = run_step(["bash", mode.build_script], root=root)
    steps.append(first)
    if first.returncode != 0:
        return finish("prepare", mode, "error", f"{mode.title} prepare failed during build.", steps, error=first.stderr or first.stdout, state_path=state_path, event_log=event_log, cache_path=cache_path)
    second = run_step(["bash", mode.package_script], root=root, env_extra={"NRF_DFU_PORT": ""})
    steps.append(second)
    if second.returncode != 0:
        return finish("prepare", mode, "error", f"{mode.title} prepare failed during DFU package creation.", steps, error=second.stderr or second.stdout, state_path=state_path, event_log=event_log, cache_path=cache_path)
    result = finish("prepare", mode, "success", f"{mode.title} build and DFU package ready.", steps, state_path=state_path, event_log=event_log, cache_path=cache_path)
    result["firmware_cache"] = write_firmware_cache("prepare", cache_path, state_path, event_log)
    write_state(result, state_path)
    return result


def prepare_all(state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG, cache_path: Path = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
    root = repo_root()
    steps: List[StepResult] = []
    for mode in MODES.values():
        first = run_step(["bash", mode.build_script], root=root)
        steps.append(first)
        if first.returncode != 0:
            return finish("prepare-cache", mode, "error", f"Prepare cache failed while building {mode.title}.", steps, error=first.stderr or first.stdout, state_path=state_path, event_log=event_log, cache_path=cache_path)
        second = run_step(["bash", mode.package_script], root=root, env_extra={"NRF_DFU_PORT": ""})
        steps.append(second)
        if second.returncode != 0:
            return finish("prepare-cache", mode, "error", f"Prepare cache failed while packaging {mode.title}.", steps, error=second.stderr or second.stdout, state_path=state_path, event_log=event_log, cache_path=cache_path)
    cache = write_firmware_cache("prepare-cache", cache_path, state_path, event_log)
    result = finish("prepare-cache", None, "success", "Both dongle firmwares built, packaged, and cached on the Raspberry Pi.", steps, state_path=state_path, event_log=event_log, cache_path=cache_path)
    result["firmware_cache"] = cache
    write_state(result, state_path)
    return result


def cache_status(state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG, cache_path: Path = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
    return write_firmware_cache("cache-status", cache_path, state_path, event_log)


def _flash_step(mode: DongleModeSpec, dfu_port: str, root: Path) -> tuple[StepResult, bool]:
    package_path = root / mode.dfu_zip
    if package_path.exists():
        return run_step(["nrfutil", "dfu", "usb-serial", "-pkg", str(package_path), "-p", dfu_port.strip()], root=root), True
    return run_step(["bash", mode.package_script], root=root, env_extra={"NRF_DFU_PORT": dfu_port.strip()}), False


def apply_mode(mode_name: str, dfu_port: str, state_path: Path = DEFAULT_STATE_PATH, event_log: Path = DEFAULT_EVENT_LOG, cache_path: Path = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
    mode = resolve_mode(mode_name)
    if not dfu_port.strip():
        return finish("switch", mode, "blocked", "DFU port required. Use --dfu-port /dev/ttyACM0 or NRF_DFU_PORT.", [], error="missing DFU port", state_path=state_path, event_log=event_log, cache_path=cache_path)
    root = repo_root()
    step, used_cache = _flash_step(mode, dfu_port.strip(), root)
    if step.returncode != 0:
        cache_hint = "Cached DFU ZIP was attempted." if used_cache else "Cached DFU ZIP was missing, so the package script was attempted."
        return finish("switch", mode, "error", f"{mode.title} DFU switch failed. {cache_hint}", [step], error=step.stderr or step.stdout, state_path=state_path, event_log=event_log, cache_path=cache_path)
    message = f"{mode.title} is now selected from the Raspberry Pi firmware cache. {mode.host_note}" if used_cache else f"{mode.title} is now selected after packaging on the Raspberry Pi. {mode.host_note}"
    result = finish("switch", mode, "success", message, [step], active_mode=mode.key, state_path=state_path, event_log=event_log, cache_path=cache_path)
    result["used_firmware_cache"] = used_cache
    result["firmware_cache"] = write_firmware_cache("switch", cache_path, state_path, event_log)
    write_state(result, state_path)
    return result


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="Koala Mode Switcher for the nRF52840 Dongle")
    parser.add_argument("action", choices=["status", "build", "package", "prepare", "prepare-all", "prepare-cache", "cache-status", "apply", "switch"])
    parser.add_argument("mode", nargs="?", default=None, help="koalabyte_lab or koala_konnect")
    parser.add_argument("--dfu-port", default=os.environ.get("NRF_DFU_PORT", ""))
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--event-log", default=str(DEFAULT_EVENT_LOG))
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    args = parser.parse_args()

    state_path = Path(args.state_path)
    event_log = Path(args.event_log)
    cache_path = Path(args.cache_path)
    try:
        if args.action == "status":
            result = status(state_path, event_log, cache_path)
        elif args.action in {"prepare-all", "prepare-cache"}:
            result = prepare_all(state_path, event_log, cache_path)
        elif args.action == "cache-status":
            result = cache_status(state_path, event_log, cache_path)
        else:
            if not args.mode:
                parser.error(f"{args.action} requires a mode")
            if args.action == "build":
                result = build(args.mode, state_path, event_log, cache_path)
            elif args.action == "package":
                result = package(args.mode, state_path, event_log, cache_path)
            elif args.action == "prepare":
                result = prepare(args.mode, state_path, event_log, cache_path)
            elif args.action in {"apply", "switch"}:
                result = apply_mode(args.mode, args.dfu_port, state_path, event_log, cache_path)
            else:
                raise ValueError(args.action)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
