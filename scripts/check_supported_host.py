#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "logs" / "preflight" / "supported_host.json"
SUPPORTED_CODENAMES = {"bookworm", "trixie"}
SUPPORTED_IDS = {"debian", "raspbian"}
MIN_PYTHON = (3, 10)
MAX_PYTHON_EXCLUSIVE = (3, 14)


def read_os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path("/etc/os-release")
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not raw or raw.lstrip().startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def read_pi_model() -> str:
    for path in (
        Path("/proc/device-tree/model"),
        Path("/sys/firmware/devicetree/base/model"),
    ):
        try:
            value = path.read_text(encoding="utf-8", errors="ignore").strip(
                "\x00\n "
            )
            if value:
                return value
        except OSError:
            pass
    return ""


def main() -> int:
    os_release = read_os_release()
    model = read_pi_model()
    is_pi = "raspberry pi" in model.lower()
    machine = platform.machine().lower()
    bits = 64 if sys.maxsize > 2**32 else 32
    python_version = sys.version_info[:3]
    failures: list[str] = []
    warnings: list[str] = []

    if platform.system() != "Linux":
        failures.append("KoalaByte deployment requires Linux")

    os_id = os_release.get("ID", "").lower()
    codename = (
        os_release.get("VERSION_CODENAME")
        or os_release.get("DEBIAN_CODENAME")
        or ""
    ).lower()
    if os_id not in SUPPORTED_IDS:
        failures.append(
            f"unsupported OS ID {os_id or 'unknown'}; use 64-bit Raspberry Pi OS Lite"
        )
    if codename not in SUPPORTED_CODENAMES:
        failures.append(
            f"unsupported OS codename {codename or 'unknown'}; supported: bookworm or trixie"
        )

    if not (MIN_PYTHON <= python_version < MAX_PYTHON_EXCLUSIVE):
        failures.append(
            "unsupported Python "
            + ".".join(map(str, python_version))
            + "; supported runtime range is 3.10 through 3.13"
        )

    if is_pi:
        if machine not in {"aarch64", "arm64"} or bits != 64:
            failures.append(
                f"Raspberry Pi firmware builds require a 64-bit OS; machine={machine}, userspace={bits}-bit"
            )
        if "3 model b plus" not in model.lower():
            warnings.append(
                f"installer is tuned for Raspberry Pi 3B+; detected {model}"
            )
    elif machine not in {"x86_64", "amd64", "aarch64", "arm64"}:
        failures.append(f"unsupported build host architecture: {machine}")

    # curl and compiler utilities are installed later by the package stage. These
    # commands must already exist for the installer to manage the host safely.
    for command in ("apt-get", "systemctl", "git"):
        if shutil.which(command) is None:
            failures.append(f"required host command is unavailable: {command}")

    payload = {
        "status": "SUPPORTED_HOST" if not failures else "UNSUPPORTED_HOST",
        "model": model,
        "is_raspberry_pi": is_pi,
        "machine": machine,
        "userspace_bits": bits,
        "python": ".".join(map(str, python_version)),
        "os_release": {
            "id": os_id,
            "codename": codename,
            "pretty_name": os_release.get("PRETTY_NAME", ""),
        },
        "supported_os_codenames": sorted(SUPPORTED_CODENAMES),
        "supported_python": ">=3.10,<3.14",
        "warnings": warnings,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
