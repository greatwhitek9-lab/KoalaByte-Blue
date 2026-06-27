#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "logs" / "one_shot" / "field_readiness_status.json"

REQUIRED_FILES = [
    "scripts/koalabyte_doctor.py",
    "scripts/koalabyte_doctor.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/install_koalabyte_boot_services.sh",
    "scripts/koalabyte_safe_mode.sh",
    "scripts/export_koalabyte_logs.sh",
    "scripts/check_koalabyte_version_handshake.py",
    "scripts/run_koalabyte_status_server.py",
    "scripts/build_koalabyte_release_package.sh",
    "systemd/koalabyte-menu.service",
    "systemd/koalabyte-menu-sync.service",
    "systemd/koalabyte-doctor.service",
    "udev/99-koalabyte-blue.rules",
    "logrotate/koalabyte-blue",
    "version/koalabyte_protocol.json",
    ".github/workflows/release-package.yml",
]


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).exists():
            failures.append(f"missing file: {relative}")

    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.exists():
            continue
        if relative.endswith(".sh"):
            rc, _out, err = run(["bash", "-n", relative])
            if rc != 0:
                failures.append(f"shell check failed for {relative}: {err.strip()}")
        if relative.endswith(".py"):
            rc, _out, err = run([sys.executable, "-m", "py_compile", relative])
            if rc != 0:
                failures.append(f"python check failed for {relative}: {err.strip()}")

    if (ROOT / "version/koalabyte_protocol.json").exists():
        try:
            payload = json.loads((ROOT / "version/koalabyte_protocol.json").read_text(encoding="utf-8"))
            if "repo_protocol_version" not in payload:
                failures.append("version manifest missing repo_protocol_version")
            if "features" not in payload:
                failures.append("version manifest missing features")
        except Exception as exc:
            failures.append(f"version manifest invalid JSON: {exc}")

    status = {
        "status": "FIELD_READINESS_READY" if not failures else "FIELD_READINESS_INCOMPLETE",
        "updated_at": time.time(),
        "required_files": REQUIRED_FILES,
        "failures": failures,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": status["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
