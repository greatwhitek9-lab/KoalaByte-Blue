#!/usr/bin/env python3
"""Terminal setup utility for the private KoalaByte Blue Ollama Cloud API key."""
from __future__ import annotations

import getpass
import json
import subprocess
import sys

HELPER = "/usr/local/sbin/koalabyte-ai-key"


def run(operation: str, secret: str | None = None) -> tuple[int, dict[str, object]]:
    try:
        result = subprocess.run(
            ["sudo", "-n", HELPER, operation],
            input=secret, capture_output=True, text=True, timeout=90, check=False,
        )
    except Exception as exc:
        return 1, {"status": "AI_SETUP_FAILED",
                   "message": f"Could not run secure helper ({type(exc).__name__}). Run the service installer first."}
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        payload = {"status": "AI_SETUP_FAILED",
                   "message": "No valid response from the secure helper; check installer/sudo configuration."}
    return result.returncode, payload


def main() -> int:
    operation = sys.argv[1].lower() if len(sys.argv) > 1 else "setup"
    if operation in {"-h", "--help", "help"}:
        print("Usage: python3 scripts/koalabyte_ai_key.py [setup|status|test|remove]")
        return 0
    if operation == "status":
        code, payload = run("status")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return code
    if operation == "test":
        code, payload = run("test-key")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return code
    if operation == "remove":
        if input("Remove the saved Ollama Cloud API key? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("Cancelled; no changes made.")
            return 0
        code, payload = run("remove-key")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return code
    if operation not in {"setup", "set"}:
        print("Unknown operation. Use setup, status, test, or remove.", file=sys.stderr)
        return 2
    print("Ollama Cloud API key setup. Input is hidden; the key is not written to shell history.")
    first = getpass.getpass("API key: ")
    second = getpass.getpass("Repeat API key: ")
    if not first or first != second:
        print("Keys were empty or did not match; nothing was saved.", file=sys.stderr)
        return 2
    code, payload = run("set-key", first)
    first = second = ""
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
