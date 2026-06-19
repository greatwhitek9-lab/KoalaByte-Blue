#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))


def main() -> int:
    from koalablue.sd_card_formatter import (
        ACTION_NAME,
        CONFIRM_PHRASE,
        DEFAULT_LABEL,
        _build_commands,
        _looks_like_whole_disk,
        _partition_path,
        _validate_label,
    )

    failures: list[str] = []
    if ACTION_NAME != "SD Card Formatter":
        failures.append("action name mismatch")
    if CONFIRM_PHRASE != "ERASE-KOALABYTE-SD":
        failures.append("confirmation phrase mismatch")
    if _validate_label("KoalaByte Blue!") != "KOALABYTEBL":
        failures.append("label sanitizer mismatch")
    if _validate_label("") != DEFAULT_LABEL:
        failures.append("empty label fallback mismatch")
    if not _looks_like_whole_disk("/dev/sda") or not _looks_like_whole_disk("/dev/mmcblk1"):
        failures.append("whole disk detector rejected expected disk names")
    if _looks_like_whole_disk("/dev/sda1") or _looks_like_whole_disk("/dev/mmcblk1p1"):
        failures.append("whole disk detector accepted partition names")
    if _partition_path("/dev/sda") != "/dev/sda1":
        failures.append("sdX partition path mismatch")
    if _partition_path("/dev/mmcblk1") != "/dev/mmcblk1p1":
        failures.append("mmcblk partition path mismatch")
    commands = _build_commands("/dev/sda", "fat32", "KOALABYTE", unmount=False)
    flattened = "\n".join(" ".join(command) for command in commands)
    for needle in ("wipefs", "parted", "mkfs.vfat", "sync"):
        if needle not in flattened:
            failures.append(f"missing planned command: {needle}")

    if failures:
        print("SD Card Formatter smoke check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("SD Card Formatter smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
