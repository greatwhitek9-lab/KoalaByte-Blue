from __future__ import annotations

from pathlib import Path
import re


LOCAL_COMMAND_ID_LIMIT = 200
EXPECTED_CONTROL_IDS = set(range(100, 108))
COMMAND_RE = re.compile(r"^\s*\{\s*(-?\d+)\s*,")


def constrain_generated_header(header: Path) -> None:
    text = header.read_text(encoding="utf-8")
    start_marker = "static const sr_cmd_t kGeneratedSpeechCommands[] = {\n"
    end_marker = "};\nconstexpr size_t kGeneratedSpeechCommandCount ="

    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError("generated voice catalog is missing the speech-command table")
    body_start = start + len(start_marker)
    end = text.find(end_marker, body_start)
    if end < 0:
        raise RuntimeError("generated voice catalog is missing the speech-command table terminator")

    kept: list[str] = []
    dropped: list[str] = []
    kept_ids: set[int] = set()

    for line in text[body_start:end].splitlines():
        match = COMMAND_RE.match(line)
        if not match:
            if line.strip():
                raise RuntimeError(f"unexpected generated speech-command line: {line!r}")
            continue
        command_id = int(match.group(1))
        if command_id < LOCAL_COMMAND_ID_LIMIT:
            kept.append(line)
            kept_ids.add(command_id)
        else:
            dropped.append(line)

    missing_controls = sorted(EXPECTED_CONTROL_IDS - kept_ids)
    if missing_controls:
        raise RuntimeError(
            "generated voice catalog lost required local K1-K8 command IDs: "
            + ", ".join(str(value) for value in missing_controls)
        )
    if not dropped:
        raise RuntimeError(
            "expected Pi-routed menu-label phrases with command IDs >= 200; "
            "refusing to silently change an unexpected generated catalog"
        )

    replacement = "\n".join(kept)
    if replacement:
        replacement += "\n"
    patched = text[:body_start] + replacement + text[end:]
    header.write_text(patched, encoding="utf-8")

    print(
        "Constrained DualEye MultiNet grammar: "
        f"local_generated_phrases={len(kept)}, "
        f"pi_routed_menu_phrases={len(dropped)}, "
        f"local_command_id_limit={LOCAL_COMMAND_ID_LIMIT}"
    )


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    constrain_generated_header(project / "include" / "generated_voice_menu_catalog.h")
elif __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    header = project / "include" / "generated_voice_menu_catalog.h"
    if not header.exists():
        raise SystemExit(
            "generated_voice_menu_catalog.h is not present; run the PlatformIO build generator first"
        )
    constrain_generated_header(header)
