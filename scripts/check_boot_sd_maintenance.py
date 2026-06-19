#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))


def main() -> int:
    from koalablue.boot_sd_maintenance import ACTION_NAME, RESET_CONFIRM_PHRASE, _is_safe_target

    failures: list[str] = []
    if ACTION_NAME != "Live Boot SD Maintenance":
        failures.append("action name mismatch")
    if RESET_CONFIRM_PHRASE != "RESET-KOALABYTE-LIVE-SD":
        failures.append("confirmation phrase mismatch")
    if _is_safe_target(REPO_ROOT):
        failures.append("repo root must not be a safe deletion target")
    if not _is_safe_target(REPO_ROOT / "logs"):
        failures.append("repo logs should be an allowed cleanup target")
    if not _is_safe_target(Path("/blecaptures")):
        failures.append("/blecaptures should be an allowed optional cleanup target")
    if _is_safe_target(Path("/")):
        failures.append("root filesystem must not be a safe deletion target")

    if failures:
        print("Live Boot SD Maintenance smoke check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Live Boot SD Maintenance smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
