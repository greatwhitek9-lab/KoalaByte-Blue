#!/usr/bin/env python3
from __future__ import annotations

from koalablue.live_menu_voice_navigation import live_menu_command_for_match
from koalablue.menu_voice_launcher import parse_menu_voice_launch
from scripts.run_headless_menu import dispatch_live_menu_command
from scripts.run_menu_screen import make_menu


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    menu_match = parse_menu_voice_launch("killerkoala menu")
    require(menu_match is not None, "killerkoala menu did not parse")
    require(
        live_menu_command_for_match(menu_match) == "main_menu",
        "main-menu voice shortcut did not map to the live main_menu command",
    )

    kruisin_match = parse_menu_voice_launch("killerkoala kruisin")
    require(kruisin_match is not None, "killerkoala kruisin did not parse")
    require(
        live_menu_command_for_match(kruisin_match) == "submenu:kruisin",
        "kruisin voice shortcut did not map to the live submenu command",
    )

    menu = make_menu()
    dispatch_live_menu_command(menu, "submenu:kruisin")
    require(menu.menu_name == "kruisin", f"live dispatcher opened {menu.menu_name!r}")
    require(menu.display_mode == "menu", "live dispatcher did not leave the menu visible")

    print("KillerKoala live voice-menu navigation check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
