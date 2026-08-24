#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
for path in (ROOT, PI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from koalablue.hdmi_display_state import (
    DEFAULT_STATE_ROOT,
    compose_scene,
    display_mode_status,
    drain_menu_commands,
    hdmi_connected,
    publish_display_event,
    read_channel_snapshots,
    read_display_mode,
    set_display_mode,
    submit_menu_command,
)
DEFAULT_STATUS = ROOT / "logs" / "one_shot" / "hdmi_display_contract.json"


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def source_contract(failures: list[str]) -> None:
    compositor = (PI_ROOT / "koalablue" / "hdmi_display.py").read_text(
        encoding="utf-8"
    )
    service = (ROOT / "systemd" / "koalabyte-hdmi.service").read_text(
        encoding="utf-8"
    )
    headless_menu = (ROOT / "scripts" / "run_headless_menu.py").read_text(
        encoding="utf-8"
    )
    launcher = (ROOT / "desktop" / "koalabyte-hdmi-toggle.desktop").read_text(
        encoding="utf-8"
    )
    require("import serial" not in compositor, "HDMI compositor must not import pyserial", failures)
    require("/dev/tty" not in compositor, "HDMI compositor must not open board tty paths", failures)
    require("pygame.init()" not in compositor, "HDMI compositor must not initialize or seize the audio mixer", failures)
    require(DEFAULT_STATE_ROOT == ROOT / "logs" / "hdmi", "HDMI state root must be independent of launcher working directory", failures)
    require("submit_menu_command" in compositor, "HDMI input must queue commands to the menu owner", failures)
    require("drain_menu_commands" in headless_menu, "headless menu must drain HDMI command requests", failures)
    for marker in (
        "scripts/run_hdmi_display.py",
        "Environment=KOALABYTE_HDMI=auto",
        "Restart=always",
        "Nice=5",
        "WantedBy=multi-user.target",
    ):
        require(marker in service, f"HDMI service missing marker: {marker}", failures)
    require(
        "scripts/set_hdmi_display_mode.py toggle" in launcher,
        "Pi OS launcher must call the persistent HDMI toggle",
        failures,
    )


def state_contract(state_root: Path, failures: list[str]) -> dict[str, Any]:
    require(read_display_mode(root=state_root) == "koalabyte", "default HDMI mode must be koalabyte", failures)
    desktop = set_display_mode("desktop", source="contract", root=state_root)
    require(desktop.get("mode") == "desktop", "desktop mode was not persisted", failures)
    toggled = set_display_mode("toggle", source="contract", root=state_root)
    require(toggled.get("mode") == "koalabyte", "toggle did not restore KoalaByte mode", failures)
    status = display_mode_status(root=state_root)
    require(bool(status.get("koalabyte_visible")), "KoalaByte visibility status is incorrect", failures)

    menu_record = publish_display_event(
        {
            "type": "menu_sync",
            "menu_title": "System / Companion",
            "selected_index": 1,
            "total_items": 3,
            "selected_label": "Show Pi OS on HDMI",
            "visible_items": [
                {"index": 0, "position": 1, "label": "HDMI Display Status", "enabled": True},
                {"index": 1, "position": 2, "label": "Show Pi OS on HDMI", "enabled": True, "selected": True},
            ],
            "password": "must-not-leak",
            "pcm_s16le_mono_b64": "must-not-leak",
        },
        root=state_root,
    )
    clean_menu = dict(menu_record.get("payload", {})) if menu_record else {}
    require("password" not in clean_menu, "HDMI state copied a password", failures)
    require("pcm_s16le_mono_b64" not in clean_menu, "HDMI state copied an audio buffer", failures)
    require(compose_scene(read_channel_snapshots(root=state_root)).get("view") == "menu", "menu scene was not selected", failures)

    time.sleep(0.002)
    publish_display_event(
        {
            "type": "killerkoala_face",
            "state": "idle",
            "message": "KillerKoala is watching the canopy",
            "left_eye": "#A54BFF",
            "right_eye": "#32FF71",
        },
        root=state_root,
    )
    require(compose_scene(read_channel_snapshots(root=state_root)).get("view") == "face", "face scene was not selected", failures)

    publish_display_event(
        {"type": "local_speech_state", "state": "speaking", "active": True},
        root=state_root,
    )
    require(bool(compose_scene(read_channel_snapshots(root=state_root)).get("speech_active")), "speech mouth state was not latched", failures)

    time.sleep(0.002)
    publish_display_event(
        {"type": "koalagotchi_status", "mood": "cheeky", "contentment": 88},
        root=state_root,
    )
    require(compose_scene(read_channel_snapshots(root=state_root)).get("view") == "koalagotchi", "Koalagotchi scene was not selected", failures)

    time.sleep(0.002)
    publish_display_event(
        {"type": "pi_execution_result", "status": "complete", "selected_label": "Bench action"},
        root=state_root,
    )
    require(compose_scene(read_channel_snapshots(root=state_root)).get("view") == "action", "action scene was not selected", failures)

    publish_display_event(
        {"type": "system_fault", "state": "error", "message": "contract alarm"},
        root=state_root,
    )
    require(compose_scene(read_channel_snapshots(root=state_root)).get("view") == "error", "error scene did not override normal views", failures)
    publish_display_event(
        {"type": "system_fault", "state": "resolved", "message": "contract recovered"},
        root=state_root,
    )
    require(not bool(compose_scene(read_channel_snapshots(root=state_root)).get("error_active")), "resolved error remained latched", failures)
    require(compose_scene({}, mode="desktop").get("view") == "desktop", "desktop mode did not release the compositor", failures)

    for command in ("up", "down", "select"):
        submit_menu_command(command, source="contract", root=state_root)
    first = drain_menu_commands(root=state_root, max_items=2)
    second = drain_menu_commands(root=state_root, max_items=2)
    require([row.get("command") for row in first] == ["up", "down"], "HDMI menu queue order is unstable", failures)
    require([row.get("command") for row in second] == ["select"], "HDMI menu queue did not preserve the remaining command", failures)
    return status


def switch_contract(state_root: Path, failures: list[str]) -> None:
    try:
        from koalablue.killerkoala_voice_control import parse_voice_command

        desktop_voice = parse_voice_command("killerkoala show pi os on hdmi")
        koalabyte_voice = parse_voice_command("killerkoala show koalabyte on hdmi")
        require(
            bool(desktop_voice.menu_action and desktop_voice.menu_action.command == "hdmi_show_desktop"),
            "voice did not resolve Show Pi OS on HDMI",
            failures,
        )
        require(
            bool(koalabyte_voice.menu_action and koalabyte_voice.menu_action.command == "hdmi_show_koalabyte"),
            "voice did not resolve Show KoalaByte on HDMI",
            failures,
        )
    except ModuleNotFoundError:
        # Source-only development hosts may not have the complete Pi voice
        # dependency set. The deployed runtime exercises the parser above;
        # here, still prove that its automatic leaf-label aliases are present.
        from koalablue.menu_catalog import leaf_menu_entries

        aliases = {
            str(row.get("label") or "").strip().lower(): str(row.get("command") or "")
            for row in leaf_menu_entries()
        }
        require(aliases.get("show pi os on hdmi") == "hdmi_show_desktop", "voice alias leaf for Pi OS is missing", failures)
        require(aliases.get("show koalabyte on hdmi") == "hdmi_show_koalabyte", "voice alias leaf for KoalaByte is missing", failures)

    from koalablue.menu_action_runner import _system_status

    desktop = _system_status("hdmi_show_desktop")
    require(desktop.get("mode") == "desktop", "menu/voice backend did not select Pi OS", failures)
    koalabyte = _system_status("hdmi_show_koalabyte")
    require(koalabyte.get("mode") == "koalabyte", "menu/voice backend did not select KoalaByte", failures)
    require(read_display_mode(root=state_root) == "koalabyte", "switch backend did not use the configured state root", failures)


def connector_contract(temp_root: Path, failures: list[str]) -> None:
    connector = temp_root / "card0-HDMI-A-1-status"
    connector.write_text("connected\n", encoding="utf-8")
    require(hdmi_connected(str(connector)), "connected HDMI status was not detected", failures)
    connector.write_text("disconnected\n", encoding="utf-8")
    require(not hdmi_connected(str(connector)), "disconnected HDMI status was treated as connected", failures)
    os.environ["KOALABYTE_HDMI"] = "off"
    require(not hdmi_connected(str(connector)), "KOALABYTE_HDMI=off was ignored", failures)
    os.environ["KOALABYTE_HDMI"] = "on"
    require(hdmi_connected(str(connector)), "KOALABYTE_HDMI=on was ignored", failures)
    os.environ["KOALABYTE_HDMI"] = "auto"


def pygame_contract(state_root: Path, failures: list[str]) -> str:
    old_environment = {
        key: os.environ.get(key)
        for key in (
            "SDL_VIDEODRIVER",
            "KOALABYTE_HDMI_WINDOWED",
            "KOALABYTE_HDMI_WIDTH",
            "KOALABYTE_HDMI_HEIGHT",
            "PYGAME_HIDE_SUPPORT_PROMPT",
        )
    }
    renderer: Any = None
    try:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["KOALABYTE_HDMI_WINDOWED"] = "1"
        os.environ["KOALABYTE_HDMI_WIDTH"] = "800"
        os.environ["KOALABYTE_HDMI_HEIGHT"] = "480"
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        try:
            import pygame as _pygame  # noqa: F401

            from koalablue.hdmi_display import PygameHDMICompositor
        except (ImportError, ModuleNotFoundError):
            return "skipped_pygame_not_installed"
        renderer = PygameHDMICompositor(state_root=state_root, fps=60)

        renderer.open()
        pygame = renderer.pygame
        scene = {
            "mode": "koalabyte",
            "view": "menu",
            "face": {
                "state": "idle",
                "message": "HDMI contract",
                "left_eye": "#A54BFF",
                "right_eye": "#32FF71",
            },
            "menu": {
                "menu_title": "System / Companion",
                "selected_index": 0,
                "total_items": 2,
                "visible_items": [
                    {"index": 0, "position": 1, "label": "Show Pi OS on HDMI", "enabled": True, "selected": True},
                    {"index": 1, "position": 2, "label": "Show KoalaByte on HDMI", "enabled": True},
                ],
            },
            "action": {},
            "error": {},
            "error_active": False,
            "koalagotchi": {"contentment": 88, "mood": "cheeky"},
            "speech_active": False,
        }
        renderer.draw(scene)
        require(renderer.screen.get_size() == (800, 480), "dummy HDMI renderer size is incorrect", failures)
        require(pygame.mixer.get_init() is None, "HDMI renderer initialized the audio mixer", failures)

        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP, "unicode": ""}))
        renderer.handle_events(scene)
        queued = drain_menu_commands(root=state_root, max_items=4)
        require([row.get("command") for row in queued] == ["up"], "HDMI keyboard input did not reach the menu queue", failures)

        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_F12, "unicode": ""}))
        renderer.handle_events(scene)
        require(read_display_mode(root=state_root) == "desktop", "F12 did not release HDMI to Pi OS", failures)
        set_display_mode("koalabyte", source="contract-reset", root=state_root)
        return "passed"
    except Exception as exc:
        failures.append(f"pygame HDMI render/input smoke failed: {exc}")
        return "failed"
    finally:
        if renderer is not None:
            try:
                renderer.close()
            except Exception:
                pass
        for key, value in old_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the KoalaByte read-only HDMI display contract")
    parser.add_argument("--status-path", default=str(DEFAULT_STATUS))
    args = parser.parse_args()
    failures: list[str] = []
    old_environment = {
        key: os.environ.get(key)
        for key in (
            "KOALABYTE_HDMI",
            "KOALABYTE_HDMI_FORCE",
            "KOALABYTE_HDMI_STATE_DIR",
            "DISPLAY",
            "WAYLAND_DISPLAY",
        )
    }
    pygame_status = "not_run"
    try:
        with tempfile.TemporaryDirectory(prefix="koalabyte-hdmi-") as temp:
            temp_root = Path(temp)
            state_root = temp_root / "state"
            os.environ["KOALABYTE_HDMI"] = "auto"
            os.environ.pop("KOALABYTE_HDMI_FORCE", None)
            os.environ.pop("DISPLAY", None)
            os.environ.pop("WAYLAND_DISPLAY", None)
            os.environ["KOALABYTE_HDMI_STATE_DIR"] = str(state_root)
            source_contract(failures)
            state_contract(state_root, failures)
            switch_contract(state_root, failures)
            connector_contract(temp_root, failures)
            pygame_status = pygame_contract(state_root, failures)
    finally:
        for key, value in old_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    payload = {
        "status": "HDMI_DISPLAY_CONTRACT_PASS" if not failures else "HDMI_DISPLAY_CONTRACT_FAIL",
        "read_only_renderer": True,
        "serial_ports_opened": False,
        "pygame_render_input_smoke": pygame_status,
        "preserved_controls": ["voice", "K1-K8", "ESP32", "Heltec", "keyboard", "touch"],
        "switch_surfaces": ["menu", "voice", "F12", "Pi OS launcher", "CLI"],
        "failures": failures,
        "updated_at": time.time(),
    }
    status_path = Path(args.status_path)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(payload["status"])
    print(f"Status: {status_path}")
    for failure in failures:
        print(f"- {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
