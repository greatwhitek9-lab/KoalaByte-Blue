#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

import koalablue  # noqa: F401 - triggers GreatWhite Reef menu extension
from koalablue.greatwhite_reef import PCAP_DIR, install_menu_catalog  # noqa: E402
from koalablue.menu_catalog import SUBMENU_ITEMS, all_menu_entries, grouped_menu_labels, menu_labels, sorted_menu_entries, submenu_title  # noqa: E402
from koalablue.menu_theme import (  # noqa: E402
    DEFAULT_JUNGLE_MENU_THEME,
    GRAPHICAL_DESCRIPTION_MAX_LINES,
    GRAPHICAL_LABEL_MAX_LINES,
    GRAPHICAL_TEXT_SAFE_PAD,
    TERMINAL_DESCRIPTION_WIDTH,
    TERMINAL_LABEL_WIDTH,
    _fit_text_for_width,
    _safe_text_width,
    _wrap_for_width,
    render_terminal_jungle_menu,
)
from scripts.run_menu_screen import make_menu, open_submenu  # noqa: E402

OUTPUT_DIR = ROOT / "logs" / "menu_actions"
STATUS_PATH = OUTPUT_DIR / "menu_theme_fit_status.json"
TERMINAL_FRAME_WIDTH = 74
MAX_TERMINAL_RENDER_LINES = 32
TEST_PCAP_NAME = "greatwhite_reef_extremely_long_selected_packet_capture_name_for_text_fit_testing_owned_lab_capture_20260628_232959.pcapng"


def _display_width(text: str) -> int:
    """Conservative printable-width guard for terminal output."""

    return len(str(text))


def _seed_long_pcap_row() -> Path:
    PCAP_DIR.mkdir(parents=True, exist_ok=True)
    path = PCAP_DIR / TEST_PCAP_NAME
    if not path.exists():
        path.write_bytes(b"KoalaByte GreatWhite Reef text-fit placeholder PCAP\n")
    install_menu_catalog()
    return path


def _open_menu_for_name(menu_name: str):
    menu = make_menu()
    if menu_name != "main":
        if not open_submenu(menu, f"submenu:{menu_name}"):
            return None
    return menu


def _list_order_checks(menu_name: str) -> list[str]:
    failures: list[str] = []
    source_labels = menu_labels(menu_name)
    sorted_labels = [str(entry.get("label", "")) for entry in sorted_menu_entries(menu_name)]
    if sorted_labels != source_labels:
        failures.append(f"{menu_name} sorted_menu_entries changed written top-to-bottom order")
    menu = _open_menu_for_name(menu_name)
    if menu is None:
        return [f"menu {menu_name} could not be opened for list-order check"]
    rendered_labels = [item.label for item in menu.items]
    if rendered_labels != source_labels:
        failures.append(f"{menu_name} rendered list order does not match written top-to-bottom order")
    for index, expected in enumerate(source_labels):
        menu.selected_index = index
        menu._clamp_scroll_to_selection()
        if menu.selected_item.label != expected:
            failures.append(f"{menu_name} row {index + 1} selected {menu.selected_item.label!r}, expected {expected!r}")
    return failures


def _terminal_fit_checks(menu_name: str) -> list[str]:
    failures: list[str] = []
    menu = _open_menu_for_name(menu_name)
    if menu is None:
        return [f"menu {menu_name} could not be opened for terminal fit check"]
    if not menu.items:
        return [f"menu {menu_name} has no renderable items"]
    for selected_index in range(len(menu.items)):
        menu.selected_index = selected_index
        menu._clamp_scroll_to_selection()
        rendered = render_terminal_jungle_menu(menu)
        lines = rendered.splitlines()
        if len(lines) > MAX_TERMINAL_RENDER_LINES:
            failures.append(f"{menu_name} selected row {selected_index + 1} renders too many terminal lines: {len(lines)}")
        for line_no, line in enumerate(lines, start=1):
            if _display_width(line) > TERMINAL_FRAME_WIDTH:
                failures.append(f"{menu_name} selected row {selected_index + 1} terminal line {line_no} exceeds {TERMINAL_FRAME_WIDTH} chars: {line}")
            if "\n" in line or "\r" in line:
                failures.append(f"{menu_name} selected row {selected_index + 1} terminal line {line_no} contains embedded newline/control text")
    return failures


def _graphical_text_checks() -> tuple[list[str], dict[str, object]]:
    failures: list[str] = []
    details: dict[str, object] = {"checked": False, "reason": ""}
    try:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame  # type: ignore

        pygame.init()
        pygame.font.init()
        item_font = pygame.font.SysFont("dejavusans", 27, bold=True)
        desc_font = pygame.font.SysFont("dejavusans", 13, bold=True)
        # Approximate 800x480 renderer row text box: 80% screen width minus panel padding.
        label_width = _safe_text_width(800 * 0.80 - 2 * 23, GRAPHICAL_TEXT_SAFE_PAD)
        desc_width = label_width
        for entry in all_menu_entries():
            label = str(entry.get("label", ""))
            command = str(entry.get("command", ""))
            description = str(entry.get("description", ""))
            candidate = f"99. {label}"
            fitted = _fit_text_for_width(item_font, candidate, int(label_width))
            if item_font.size(fitted)[0] > label_width:
                failures.append(f"graphical label overflow after fit: {label}")
            if fitted and fitted[-1] == "…" and len(fitted) > len(candidate):
                failures.append(f"graphical label ellipsis expanded text unexpectedly: {label}")
            wrapped = _wrap_for_width(desc_font, description, int(desc_width), GRAPHICAL_DESCRIPTION_MAX_LINES)
            if len(wrapped) > GRAPHICAL_DESCRIPTION_MAX_LINES:
                failures.append(f"graphical description exceeds max lines: {label} / {command}")
            for line in wrapped:
                if desc_font.size(line)[0] > desc_width:
                    failures.append(f"graphical description overflow after wrap: {label} / {line}")
        details = {"checked": True, "label_width_px": label_width, "description_width_px": desc_width}
        pygame.quit()
    except Exception as exc:
        failures.append(f"graphical font fit check could not run: {exc}")
        details = {"checked": False, "reason": str(exc)}
    return failures, details


def main() -> int:
    failures: list[str] = []
    seeded_pcap = _seed_long_pcap_row()
    theme = DEFAULT_JUNGLE_MENU_THEME
    if "jungle" not in theme.border_style or "eucalyptus" not in theme.border_style:
        failures.append("menu theme identity missing")
    if theme.font_family != theme.item_font_family:
        failures.append("menu font stacks diverged")
    if getattr(theme, "keyboard_input_font_family", theme.item_font_family) != theme.item_font_family:
        failures.append("keyboard input font stack diverged")
    if GRAPHICAL_LABEL_MAX_LINES != 1 or GRAPHICAL_DESCRIPTION_MAX_LINES > 2:
        failures.append("graphical menu text limits changed")
    if TERMINAL_LABEL_WIDTH > 68 or TERMINAL_DESCRIPTION_WIDTH > 64:
        failures.append("terminal label/description widths are too wide for the border frame")

    menu_names = ["main", *SUBMENU_ITEMS.keys()]
    for menu_name in menu_names:
        if not submenu_title(menu_name):
            failures.append(f"menu {menu_name} has no title")
        if not any(grouped_menu_labels(menu_name).values()):
            failures.append(f"menu {menu_name} has no visible labels")
        failures.extend(_list_order_checks(menu_name))
        failures.extend(_terminal_fit_checks(menu_name))

    graphical_failures, graphical_details = _graphical_text_checks()
    failures.extend(graphical_failures)

    payload = {
        "status": "MENU_THEME_FIT_READY" if not failures else "MENU_THEME_FIT_INCOMPLETE",
        "theme": {
            "title": theme.title,
            "font_family": theme.font_family,
            "item_font_family": theme.item_font_family,
            "keyboard_input_font_family": getattr(theme, "keyboard_input_font_family", ""),
            "border_style": theme.border_style,
        },
        "menu_names": menu_names,
        "catalog_entry_count": len(all_menu_entries()),
        "terminal_frame_width": TERMINAL_FRAME_WIDTH,
        "terminal_label_width": TERMINAL_LABEL_WIDTH,
        "terminal_description_width": TERMINAL_DESCRIPTION_WIDTH,
        "graphical_label_max_lines": GRAPHICAL_LABEL_MAX_LINES,
        "graphical_description_max_lines": GRAPHICAL_DESCRIPTION_MAX_LINES,
        "graphical_text_safe_pad": GRAPHICAL_TEXT_SAFE_PAD,
        "long_pcap_fit_fixture": str(seeded_pcap),
        "graphical_fit": graphical_details,
        "list_order": "explicit top-to-bottom source order; group metadata does not reorder rows",
        "failures": failures,
        "updated_at": time.time(),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
