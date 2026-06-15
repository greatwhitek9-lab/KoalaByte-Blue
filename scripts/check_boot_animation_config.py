#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "firmware" / "esp32-dualeye" / "include" / "config.h"
PLATFORMIO = REPO_ROOT / "firmware" / "esp32-dualeye" / "platformio.ini"
MAIN = REPO_ROOT / "firmware" / "esp32-dualeye" / "src" / "main.cpp"
BOOT = REPO_ROOT / "firmware" / "esp32-dualeye" / "src" / "boot_animation.cpp"
FW_MENU_THEME_H = REPO_ROOT / "firmware" / "esp32-dualeye" / "include" / "menu_theme.h"
FW_MENU_THEME_CPP = REPO_ROOT / "firmware" / "esp32-dualeye" / "src" / "menu_theme.cpp"
PI_MENU_THEME = REPO_ROOT / "pi-companion" / "koalablue" / "menu_theme.py"
PI_MENU_UI = REPO_ROOT / "pi-companion" / "koalblue" / "menu_ui.py"
PI_MENU_UI_ALT = REPO_ROOT / "pi-companion" / "koalablue" / "menu_ui.py"
PI_MENU_SCREEN = REPO_ROOT / "pi-companion" / "koalablue" / "menu_screen.py"
PI_KOALA_KRY = REPO_ROOT / "pi-companion" / "koalablue" / "koala_kry.py"
MENU_CATALOG = REPO_ROOT / "pi-companion" / "koalablue" / "menu_catalog.py"
RUN_MENU = REPO_ROOT / "scripts" / "run_menu_screen.py"
DEFAULT_CONFIG = REPO_ROOT / "pi-companion" / "config.default.json"

REQUIRED = {
    CONFIG: [
        "#define ENABLE_DISPLAY_BOOT_ANIMATION 1",
        "#define BOOT_ANIMATION_TOTAL_MS",
        "#define DISPLAY_ROTATION",
    ],
    PLATFORMIO: [
        "bodmer/TFT_eSPI",
    ],
    MAIN: [
        '#include "boot_animation.h"',
        "setupDisplay();",
        "runBootAnimation();",
        'doc["boot_animation"] = ENABLE_DISPLAY_BOOT_ANIMATION;',
    ],
    BOOT: [
        "void setupDisplay()",
        "void runBootAnimation()",
        "KoalaByte",
        "Blue",
        "BOOTING...",
    ],
    FW_MENU_THEME_H: [
        "drawEucalyptusMenuBorder",
        "drawJungleMenuTitle",
        "drawJungleMenuItem",
    ],
    FW_MENU_THEME_CPP: [
        "drawEucalyptusMenuBorder",
        "drawJungleMenuTitle",
        "drawJungleMenuItem",
        "drawBubbleText",
    ],
    PI_MENU_THEME: [
        "JungleMenuTheme",
        "JungleMenuRenderer",
        "render_terminal_jungle_menu",
        "eucalyptus_branches",
    ],
    PI_MENU_UI_ALT: [
        "render_terminal_jungle_menu",
        "RevA14 jungle/eucalyptus theme",
    ],
    PI_MENU_SCREEN: [
        "render_terminal_jungle_menu",
    ],
    PI_KOALA_KRY: [
        "request_rf_transmit",
        "KoalaKryTransmitReview",
        "blocked_no_over_the_air_replay",
        "--request-rf-transmit",
    ],
    MENU_CATALOG: [
        "Koala Kry RF Review",
        "koala_kry_transmit_review",
    ],
    RUN_MENU: [
        "--graphical",
        "JungleMenuRenderer",
    ],
    DEFAULT_CONFIG: [
        "RevA14 Jungle Book style eucalyptus menu",
        "eucalyptus_branches",
        "font_family_candidates",
        "rf_transmit_request_policy",
        "blocked_review_manifest_only",
        "Koala Kry RF Review",
    ],
}


def main() -> int:
    failures: list[str] = []
    for path, needles in REQUIRED.items():
        if not path.exists():
            failures.append(f"missing file: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                failures.append(f"missing '{needle}' in {path.relative_to(REPO_ROOT)}")
    if failures:
        print("KoalaByte Blue boot/menu/Kry config check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("KoalaByte Blue boot/menu/Kry config check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
