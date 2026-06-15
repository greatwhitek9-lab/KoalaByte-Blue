#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_COMPANION = REPO_ROOT / "pi-companion"
if str(PI_COMPANION) not in sys.path:
    sys.path.insert(0, str(PI_COMPANION))

from koalablue.boot_animation import BootAnimationConfig, BootSplashUnavailable, run_boot_splash


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the KoalaByte Blue animated boot splash")
    parser.add_argument("--duration", type=float, default=3.0, help="Splash duration in seconds")
    parser.add_argument("--fps", type=int, default=30, help="Animation frames per second")
    parser.add_argument("--windowed", action="store_true", help="Run in a window instead of fullscreen")
    parser.add_argument("--width", type=int, default=800, help="Window width when --windowed is used")
    parser.add_argument("--height", type=int, default=480, help="Window height when --windowed is used")
    args = parser.parse_args()

    config = BootAnimationConfig(
        duration_seconds=args.duration,
        fps=args.fps,
        fullscreen=not args.windowed,
        width=args.width,
        height=args.height,
    )

    try:
        return run_boot_splash(config)
    except BootSplashUnavailable as exc:
        print(f"KoalaByte Blue boot splash skipped: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
