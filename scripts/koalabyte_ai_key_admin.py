#!/usr/bin/env python3
"""Root-owned API-key manager; secret material is accepted only on stdin."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ENV_FILE = Path("/etc/koalabyte-blue/killerkoala.env")
SERVICE = "koalabyte-dualeye-voice-bridge.service"
ALLOWED = {"set-key", "test-key", "remove-key", "status"}
KEY_RE = re.compile(r"^[A-Za-z0-9._~+/=-]{8,4096}$")
API_URL = "https://ollama.com/api/chat"


def read_env() -> tuple[list[str], str, str, str]:
    if ENV_FILE.is_symlink() or not ENV_FILE.is_file():
        raise RuntimeError("Private settings file is missing or is an unsafe symlink; run the service installer first.")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    mode, key, model = "local", "", "gemma4:31b"
    for line in lines:
        for name, current in (("KILLERKOALA_AI_MODE", "mode"), ("OLLAMA_API_KEY", "key"),
                              ("KILLERKOALA_ONLINE_LLM_MODEL", "model")):
            match = re.match(r"^\s*" + name + r"\s*=\s*(.*?)\s*$", line)
            if not match:
                continue
            value = match.group(1).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if current == "mode":
                mode = value.lower() or "local"
            elif current == "key":
                key = value
            else:
                model = value or model
    return lines, mode if mode in {"local", "online"} else "local", key, model


def atomic_write(lines: list[str]) -> None:
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


def replace_setting(lines: list[str], name: str, value: str | None) -> list[str]:
    result: list[str] = []
    replaced = False
    for line in lines:
        if re.match(r"^\s*" + re.escape(name) + r"\s*=", line):
            if not replaced and value is not None:
                result.append(f"{name}={value}")
                replaced = True
        else:
            result.append(line)
    if not replaced and value is not None:
        result.append(f"{name}={value}")
    return result


def validate_key(key: str, model: str) -> tuple[bool, str]:
    if not KEY_RE.fullmatch(key):
        return False, "Key format is unsupported. Use the API key exactly as issued; whitespace/control characters are not accepted."
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "stream": False,
        "options": {"num_predict": 1},
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            if 200 <= response.status < 300:
                return True, "Ollama Cloud accepted the key and completed a minimal test request."
            return False, f"Ollama Cloud returned HTTP {response.status}."
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return False, f"Ollama Cloud rejected authentication (HTTP {exc.code})."
        return False, f"Ollama Cloud validation failed with HTTP {exc.code}."
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, "Could not reach Ollama Cloud. Check network access and try again."


def restart_service() -> bool:
    try:
        return subprocess.run(["systemctl", "restart", SERVICE], capture_output=True,
                              text=True, timeout=45, check=False).returncode == 0
    except Exception:
        return False


def emit(status: str, mode: str, configured: bool, **extra: object) -> None:
    print(json.dumps({"status": status, "ai_mode": mode,
                      "online_api_key_configured": configured, **extra}))


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ALLOWED:
        print("Usage: koalabyte-ai-key {set-key|test-key|remove-key|status}", file=sys.stderr)
        return 2
    operation = sys.argv[1]
    try:
        lines, mode, key, model = read_env()
        configured = bool(KEY_RE.fullmatch(key))
        if operation == "status":
            emit("AI_KEY_STATUS", mode, configured)
            return 0
        if operation == "test-key":
            if not configured:
                emit("AI_MODE_NEEDS_API_KEY", mode, False, message="No API key is configured.")
                return 2
            valid, message = validate_key(key, model)
            emit("AI_KEY_VALID" if valid else "AI_KEY_INVALID", mode, True,
                 message=message, test_request_sent=True)
            return 0 if valid else 1
        if operation == "set-key":
            new_key = sys.stdin.read(4097).strip()
            if not KEY_RE.fullmatch(new_key):
                emit("AI_KEY_INVALID_INPUT", mode, configured,
                     message="Key format is unsupported or key length is invalid.")
                return 2
            valid, message = validate_key(new_key, model)
            if not valid:
                emit("AI_KEY_VALIDATION_FAILED", mode, configured, message=message,
                     test_request_sent=True)
                return 1
            updated = replace_setting(lines, "OLLAMA_API_KEY", new_key)
            atomic_write(updated)
            if mode == "online" and not restart_service():
                atomic_write(lines)
                restart_service()
                emit("AI_KEY_SAVE_FAILED_ROLLED_BACK", mode, configured,
                     message="Service restart failed; the previous key was restored.")
                return 1
            emit("AI_KEY_SAVED", mode, True,
                 message="API key validated and saved securely. No key value is displayed.")
            return 0
        # Remove key and force local mode if online AI was active.
        updated = replace_setting(lines, "OLLAMA_API_KEY", "")
        target_mode = "local" if mode == "online" else mode
        if target_mode != mode:
            updated = replace_setting(updated, "KILLERKOALA_AI_MODE", target_mode)
        atomic_write(updated)
        if not restart_service():
            atomic_write(lines)
            restart_service()
            emit("AI_KEY_REMOVE_FAILED_ROLLED_BACK", mode, configured,
                 message="Service restart failed; previous settings were restored.")
            return 1
        emit("AI_KEY_REMOVED", target_mode, False,
             message="API key removed. Local AI is active if online mode was previously selected.")
        return 0
    except Exception as exc:
        emit("AI_KEY_ERROR", "local", False,
             message=f"Secure key operation failed ({type(exc).__name__}).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
