#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS = ROOT / "logs" / "runtime" / "live_service_health.json"
MAX_RESTARTS = int(os.getenv("KOALABYTE_MAX_SERVICE_RESTARTS", "3"))


def systemctl_properties(service: str) -> dict[str, str]:
    command = [
        "systemctl",
        "show",
        service,
        "--property=ActiveState,SubState,NRestarts,ExecMainStatus,Result",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception as exc:
        return {"error": str(exc)}
    payload: dict[str, str] = {
        "returncode": str(result.returncode),
        "stderr": result.stderr.strip(),
    }
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key] = value
    return payload


def service_ready(service: str) -> tuple[bool, dict[str, str]]:
    properties = systemctl_properties(service)
    try:
        restarts = int(properties.get("NRestarts", "0") or 0)
    except ValueError:
        restarts = MAX_RESTARTS + 1
    ready = (
        properties.get("returncode") == "0"
        and properties.get("ActiveState") == "active"
        and properties.get("SubState") in {"running", "exited"}
        and properties.get("ExecMainStatus") in {"", "0"}
        and properties.get("Result") in {"", "success"}
        and restarts <= MAX_RESTARTS
    )
    properties["restart_limit"] = str(MAX_RESTARTS)
    return ready, properties


def json_request(
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 6.0,
) -> dict[str, Any]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(1024 * 1024)
    decoded = json.loads(body.decode("utf-8", errors="strict"))
    if not isinstance(decoded, dict):
        raise RuntimeError(f"expected JSON object from {url}")
    return decoded


def socket_is_ready(path: Path) -> bool:
    try:
        return stat.S_ISSOCK(path.stat().st_mode)
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Require stable KoalaByte services, serial owners, and local APIs"
    )
    parser.add_argument("--skip-firmware", action="store_true")
    parser.add_argument("--firmware-build-only", action="store_true")
    parser.add_argument("--skip-ai", action="store_true")
    parser.add_argument("--skip-music", action="store_true")
    parser.add_argument("--require-can", action="store_true")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--status-path", default=str(DEFAULT_STATUS))
    args = parser.parse_args()

    firmware_runtime = not args.skip_firmware and not args.firmware_build_only
    required_services = [
        "koalabyte-menu.service",
        "koalabyte-doctor.service",
    ]
    if firmware_runtime:
        required_services.extend(
            [
                "koalabyte-ble-node-manager.service",
                "koalabyte-dualeye-voice-bridge.service",
            ]
        )
    if not args.skip_ai:
        required_services.append("ollama.service")
    if not args.skip_music:
        required_services.append("mopidy.service")
    if args.require_can:
        required_services.append("koalabyte-can0.service")

    deadline = time.monotonic() + max(1, args.timeout)
    last_services: dict[str, dict[str, str]] = {}
    last_api: dict[str, Any] = {}
    failures: list[str] = []

    while time.monotonic() < deadline:
        failures = []
        last_services = {}
        for service in required_services:
            ready, properties = service_ready(service)
            last_services[service] = properties
            if not ready:
                restarts = properties.get("NRestarts", "unknown")
                failures.append(
                    f"service not stable: {service} (restarts={restarts})"
                )

        if firmware_runtime:
            for target in ("esp32", "heltec"):
                path = ROOT / "logs" / "runtime" / "serial_bus" / f"{target}.sock"
                if not socket_is_ready(path):
                    failures.append(f"serial owner socket missing: {path}")

        last_api = {}
        if not args.skip_ai:
            try:
                tags = json_request(
                    os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
                    + "/api/tags"
                )
                names = {
                    str(item.get("name") or item.get("model") or "")
                    for item in tags.get("models", [])
                    if isinstance(item, dict)
                }
                required_model = os.getenv(
                    "KILLERKOALA_LLM_MODEL", "killerkoala-tinyllama:latest"
                )
                last_api["ollama"] = {
                    "ready": required_model in names,
                    "required_model": required_model,
                    "models": sorted(name for name in names if name),
                }
                if required_model not in names:
                    failures.append(
                        f"Ollama API is reachable but model is missing: {required_model}"
                    )
            except Exception as exc:
                last_api["ollama"] = {"ready": False, "error": str(exc)}
                failures.append(f"Ollama API is not ready: {exc}")

        if not args.skip_music:
            try:
                rpc_url = os.getenv(
                    "KOALABYTE_MOPIDY_RPC_URL",
                    "http://127.0.0.1:6680/mopidy/rpc",
                )
                response = json_request(
                    rpc_url,
                    payload={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "core.playback.get_state",
                    },
                )
                ready = response.get("id") == 1 and "result" in response
                last_api["mopidy"] = {
                    "ready": ready,
                    "playback_state": response.get("result"),
                    "error": response.get("error"),
                }
                if not ready:
                    failures.append("Mopidy JSON-RPC did not return a playback state")
            except Exception as exc:
                last_api["mopidy"] = {"ready": False, "error": str(exc)}
                failures.append(f"Mopidy JSON-RPC is not ready: {exc}")

        if not failures:
            break
        time.sleep(1.0)

    payload = {
        "status": "LIVE_RUNTIME_READY" if not failures else "LIVE_RUNTIME_INCOMPLETE",
        "required_services": required_services,
        "services": last_services,
        "apis": last_api,
        "max_service_restarts": MAX_RESTARTS,
        "serial_owners_required": firmware_runtime,
        "serial_owner_sockets": {
            target: str(
                ROOT / "logs" / "runtime" / "serial_bus" / f"{target}.sock"
            )
            for target in ("esp32", "heltec")
        },
        "failures": failures,
        "updated_at": time.time(),
    }
    output = Path(args.status_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
