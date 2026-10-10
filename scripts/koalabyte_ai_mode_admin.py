#!/usr/bin/env python3
"""Root-owned, narrowly scoped mode switch for the KoalaByte menu."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ENV_FILE = Path("/etc/koalabyte-blue/killerkoala.env")
SERVICE = "koalabyte-dualeye-voice-bridge.service"


def read_settings() -> tuple[list[str], str, bool]:
    if not ENV_FILE.is_file():
        raise RuntimeError(f"Private settings file is missing: {ENV_FILE}")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    mode = "local"
    key_configured = False
    for line in lines:
        match = re.match(r"^\s*KILLERKOALA_AI_MODE\s*=\s*(.*?)\s*$", line)
        if match:
            mode = match.group(1).strip().strip("\"'").lower() or "local"
        match = re.match(r"^\s*OLLAMA_API_KEY\s*=\s*(.*?)\s*$", line)
        if match:
            value = match.group(1).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            key_configured = bool(value and value.lower() not in {"your_ollama_api_key", "replace_me"})
    if mode not in {"local", "online"}:
        mode = "local"
    return lines, mode, key_configured


def atomic_write(lines: list[str]) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".killerkoala.env.", dir=str(ENV_FILE.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write("\n".join(lines).rstrip() + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, ENV_FILE)
        os.chmod(ENV_FILE, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def emit(status: str, mode: str, key_configured: bool, **extra: object) -> None:
    print(json.dumps({
        "status": status,
        "ai_mode": mode,
        "online_api_key_configured": key_configured,
        "service": SERVICE,
        **extra,
    }))


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"local", "online", "status"}:
        print("Usage: koalabyte-ai-mode {local|online|status}", file=sys.stderr)
        return 2
    requested = sys.argv[1]
    try:
        lines, current_mode, key_configured = read_settings()
        if requested == "status":
            emit("AI_MODE_STATUS", current_mode, key_configured)
            return 0
        if requested == "online" and not key_configured:
            emit("AI_MODE_NEEDS_API_KEY", current_mode, False,
                 message="Configure OLLAMA_API_KEY in /etc/koalabyte-blue/killerkoala.env first.")
            return 2
        if requested == current_mode:
            emit("AI_MODE_UNCHANGED", current_mode, key_configured)
            return 0
        updated: list[str] = []
        replaced = False
        for line in lines:
            if re.match(r"^\s*KILLERKOALA_AI_MODE\s*=", line):
                if not replaced:
                    updated.append(f"KILLERKOALA_AI_MODE={requested}")
                    replaced = True
            else:
                updated.append(line)
        if not replaced:
            updated.append(f"KILLERKOALA_AI_MODE={requested}")
        atomic_write(updated)
        result = subprocess.run(
            ["systemctl", "restart", SERVICE],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if result.returncode != 0:
            atomic_write(lines)
            subprocess.run(
                ["systemctl", "restart", SERVICE],
                check=False,
                capture_output=True,
                text=True,
                timeout=45,
            )
            emit("AI_MODE_RESTART_FAILED_ROLLED_BACK", current_mode, key_configured,
                 message=(result.stderr or result.stdout or "systemctl restart failed").strip()[:600])
            return 1
        emit("AI_MODE_UPDATED", requested, key_configured,
             message="KillerKoala service restarted using the selected AI mode.")
        return 0
    except Exception as exc:
        print(json.dumps({"status": "AI_MODE_ERROR", "error": str(exc)[:600]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
