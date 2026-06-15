#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "firmware" / "esp32-dualeye" / "include" / "config.h"
PLATFORMIO = REPO_ROOT / "firmware" / "esp32-dualeye" / "platformio.ini"
MAIN = REPO_ROOT / "firmware" / "esp32-dualeye" / "src" / "main.cpp"
BOOT = REPO_ROOT / "firmware" / "esp32-dualeye" / "src" / "boot_animation.cpp"

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
        print("KoalaByte Blue boot animation config check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("KoalaByte Blue boot animation config check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
