from __future__ import annotations

import argparse
import json
import os
import select
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .koala_mode_switcher import DEFAULT_ACTIVE_MODE, DEFAULT_EVENT_LOG, DEFAULT_STATE_PATH, MODES, apply_mode, load_state, resolve_mode

DEFAULT_PREBOOT_STATE_PATH = Path("logs/preboot_mode_selection.json")
DEFAULT_TIMEOUT_SECONDS = 8.0


@dataclass(frozen=True)
class PrebootModeChoice:
    key: str
    title: str
    short_label: str
    description: str


PREBOOT_CHOICES: Dict[str, PrebootModeChoice] = {
    "koalabyte_lab": PrebootModeChoice(
        key="koalabyte_lab",
        title="KoalaByte Blue Lab Mode",
        short_label="Lab",
        description="Default production/lab mode. The nRF52840 Dongle advertises as KoalaByte Lab for owned-device BLE scan testing.",
    ),
    "koala_konnect": PrebootModeChoice(
        key="koala_konnect",
        title="Koala Konnect Mode",
        short_label="Konnect",
        description="External USB HCI adapter mode. Replug the dongle into the phone or computer host USB port after switching.",
    ),
}

SELECTION_ALIASES = {
    "1": "koalabyte_lab",
    "l": "koalabyte_lab",
    "lab": "koalabyte_lab",
    "koalabyte": "koalabyte_lab",
    "koalabyte lab": "koalabyte_lab",
    "koalabyte blue lab": "koalabyte_lab",
    "koalabye blue lab": "koalabyte_lab",
    "koalabyte_lab": "koalabyte_lab",
    "2": "koala_konnect",
    "k": "koala_konnect",
    "konnect": "koala_konnect",
    "koala konnect": "koala_konnect",
    "koala_konnect": "koala_konnect",
    "adapter": "koala_konnect",
    "external adapter": "koala_konnect",
}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _resolve_default_mode(default_mode: str, state_path: Path) -> str:
    if default_mode == "current":
        current = str(load_state(state_path).get("active_mode", DEFAULT_ACTIVE_MODE))
        return current if current in PREBOOT_CHOICES else DEFAULT_ACTIVE_MODE
    return resolve_mode(default_mode).key


def _resolve_selection(value: str, fallback: str) -> str:
    normalized = value.strip().lower().replace("-", " ").replace("_", " ")
    if not normalized:
        return fallback
    key = SELECTION_ALIASES.get(normalized, normalized.replace(" ", "_"))
    return resolve_mode(key).key


def _write_preboot_state(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def _append_preboot_event(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_jsonable(payload), sort_keys=True) + "\n")


def _prompt_line(timeout_seconds: float) -> Optional[str]:
    if not sys.stdin.isatty():
        return None
    try:
        ready, _out, _err = select.select([sys.stdin], [], [], max(0.0, timeout_seconds))
    except (OSError, ValueError):
        ready = []
    if not ready:
        return ""
    return sys.stdin.readline().strip()


def render_prompt(default_mode: str, timeout_seconds: float) -> str:
    default_choice = PREBOOT_CHOICES[default_mode]
    lines = [
        "",
        "KoalaByte Blue Pre-Boot Dongle Mode Selector",
        "================================================",
        "Choose the nRF52840 Dongle profile before the normal KoalaByte Blue boot/menu flow.",
        "",
        f"1) {PREBOOT_CHOICES['koalabyte_lab'].title}",
        f"   {PREBOOT_CHOICES['koalabyte_lab'].description}",
        f"2) {PREBOOT_CHOICES['koala_konnect'].title}",
        f"   {PREBOOT_CHOICES['koala_konnect'].description}",
        "",
        f"Press 1/L for Lab, 2/K for Konnect, or Enter for default: {default_choice.title}.",
        f"Auto-selects default in {timeout_seconds:.0f} seconds.",
        "Selection> ",
    ]
    return "\n".join(lines)


def select_mode(
    *,
    mode: Optional[str] = None,
    default_mode: str = DEFAULT_ACTIVE_MODE,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    state_path: Path = DEFAULT_STATE_PATH,
    preboot_state_path: Path = DEFAULT_PREBOOT_STATE_PATH,
    event_log: Path = DEFAULT_EVENT_LOG,
    dfu_port: str = "",
    force_flash: bool = False,
    no_apply: bool = False,
    noninteractive: bool = False,
) -> Dict[str, Any]:
    default_key = _resolve_default_mode(default_mode, state_path)
    state_before = load_state(state_path)
    current_key = str(state_before.get("active_mode", DEFAULT_ACTIVE_MODE))
    if current_key not in PREBOOT_CHOICES:
        current_key = DEFAULT_ACTIVE_MODE

    if mode:
        selected_key = _resolve_selection(mode, default_key)
        selection_source = "argument"
    elif noninteractive or not sys.stdin.isatty():
        selected_key = default_key
        selection_source = "noninteractive_default"
    else:
        sys.stdout.write(render_prompt(default_key, timeout_seconds))
        sys.stdout.flush()
        raw = _prompt_line(timeout_seconds)
        selected_key = _resolve_selection(raw or "", default_key)
        selection_source = "timeout_default" if raw == "" else "interactive"

    selected_choice = PREBOOT_CHOICES[selected_key]
    base_payload: Dict[str, Any] = {
        "action": "preboot-dongle-mode-select",
        "selected_mode": selected_key,
        "selected_title": selected_choice.title,
        "selected_short_label": selected_choice.short_label,
        "selection_source": selection_source,
        "current_mode_before": current_key,
        "current_title_before": PREBOOT_CHOICES[current_key].title,
        "default_mode": default_key,
        "dfu_port": dfu_port,
        "force_flash": force_flash,
        "no_apply": no_apply,
        "updated_at": time.time(),
        "preboot_state_path": str(preboot_state_path),
        "mode_switcher_state_path": str(state_path),
        "event_log": str(event_log),
        "boot_flow_note": "Run this selector before the KoalaByte Blue boot splash/menu process.",
        "safety": {
            "single_dongle_profile_installed_at_a_time": True,
            "koalabyte_lab_default": True,
            "dfu_required_to_change_physical_dongle_firmware": True,
        },
    }

    if selected_key == current_key and not force_flash:
        result = {
            **base_payload,
            "status": "success",
            "mode_switch_status": "unchanged",
            "message": f"{selected_choice.title} already appears selected; continuing boot without reflashing.",
            "next_step": "Continue to KoalaByte Blue boot splash and main menu.",
        }
        _write_preboot_state(result, preboot_state_path)
        _append_preboot_event(result, event_log)
        return result

    if no_apply or not dfu_port.strip():
        result = {
            **base_payload,
            "status": "selected_not_applied",
            "mode_switch_status": "dfu_not_run",
            "message": f"{selected_choice.title} was selected, but the nRF52840 Dongle was not flashed because no DFU port was provided.",
            "next_step": f"Put the dongle in DFU bootloader mode and run: NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode {selected_key}",
        }
        _write_preboot_state(result, preboot_state_path)
        _append_preboot_event(result, event_log)
        return result

    switch_result = apply_mode(selected_key, dfu_port.strip(), state_path, event_log)
    status = "success" if switch_result.get("status") == "success" else "error"
    result = {
        **base_payload,
        "status": status,
        "mode_switch_status": switch_result.get("status"),
        "message": switch_result.get("message", f"{selected_choice.title} switch attempted."),
        "next_step": "Continue to KoalaByte Blue boot splash and main menu." if status == "success" else "Check DFU port, dongle bootloader state, and mode package logs before continuing.",
        "switch_result": switch_result,
    }
    _write_preboot_state(result, preboot_state_path)
    _append_preboot_event(result, event_log)
    return result


def run_cli(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="KoalaByte Blue pre-boot nRF52840 Dongle mode selector")
    parser.add_argument("--mode", default=None, help="koalabyte_lab/lab or koala_konnect/konnect. Omit for interactive prompt.")
    parser.add_argument("--default-mode", default="current", help="Default on timeout: current, koalabyte_lab, or koala_konnect")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Interactive timeout in seconds")
    parser.add_argument("--dfu-port", default=os.environ.get("NRF_DFU_PORT", ""), help="nRF52840 Dongle DFU serial port, for example /dev/ttyACM0")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH), help="Koala Mode Switcher state JSON path")
    parser.add_argument("--preboot-state-path", default=str(DEFAULT_PREBOOT_STATE_PATH), help="Pre-boot selection state JSON path")
    parser.add_argument("--event-log", default=str(DEFAULT_EVENT_LOG), help="Mode/preboot event log path")
    parser.add_argument("--force-flash", action="store_true", help="Flash selected mode even if it already appears active")
    parser.add_argument("--no-apply", action="store_true", help="Record selected mode but do not run DFU flash")
    parser.add_argument("--noninteractive", action="store_true", help="Do not prompt; use --mode or default")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        result = select_mode(
            mode=args.mode,
            default_mode=args.default_mode,
            timeout_seconds=args.timeout,
            state_path=Path(args.state_path),
            preboot_state_path=Path(args.preboot_state_path),
            event_log=Path(args.event_log),
            dfu_port=args.dfu_port,
            force_flash=args.force_flash,
            no_apply=args.no_apply,
            noninteractive=args.noninteractive,
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
    return 0 if result.get("status") in {"success", "selected_not_applied"} else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
