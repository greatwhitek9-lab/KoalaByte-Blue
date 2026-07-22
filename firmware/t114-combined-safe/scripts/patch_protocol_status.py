#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

PROTOCOL = "killerkoala_face_v1"
REPO_PROTOCOL_VERSION = "2026.06-menu-sync-v1"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"T114 protocol patch expected exactly one {label} anchor, found {count}"
        )
    return text.replace(old, new, 1)


def patch(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '#define KOALA_FW "0.10.0-t114-smooth-idle-and-speech-mouth"\n',
        '#define KOALA_FW "0.10.0-t114-smooth-idle-and-speech-mouth"\n'
        f'#define KOALA_PROTOCOL "{PROTOCOL}"\n'
        f'#define KOALA_REPO_PROTOCOL_VERSION "{REPO_PROTOCOL_VERSION}"\n',
        "firmware protocol declarations",
    )
    text = replace_once(
        text,
        '\\"speaking\\":%s,\\"fw\\":\\"%s\\",\\"uptime_ms\\":%lld',
        '\\"speaking\\":%s,\\"fw\\":\\"%s\\",'
        '\\"protocol\\":\\"%s\\",'
        '\\"repo_protocol_version\\":\\"%s\\",'
        '\\"uptime_ms\\":%lld',
        "mouth status protocol fields",
    )
    text = replace_once(
        text,
        'mouth_blend_amount, speaking_active ? "true" : "false", KOALA_FW,\n'
        '            (long long)(k_uptime_get() - boot_ms));',
        'mouth_blend_amount, speaking_active ? "true" : "false", KOALA_FW,\n'
        '            KOALA_PROTOCOL, KOALA_REPO_PROTOCOL_VERSION,\n'
        '            (long long)(k_uptime_get() - boot_ms));',
        "mouth status protocol arguments",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    patch(Path(args.source), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
