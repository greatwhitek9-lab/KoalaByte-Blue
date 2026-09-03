from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .bounded_log import append_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = Path(os.getenv("KOALABYTE_EUCALYPTUS_RUNTIME_DIR", "logs/eucalyptus"))
PID_PATH = RUNTIME_DIR / "eucalyptus_worker.pid"
STATUS_PATH = RUNTIME_DIR / "eucalyptus_worker_status.json"
CAPTURE_PATH = RUNTIME_DIR / "eucalyptus_live.jsonl"
STDOUT_PATH = RUNTIME_DIR / "eucalyptus_worker.out.log"
STDERR_PATH = RUNTIME_DIR / "eucalyptus_worker.err.log"
SCAN_SECONDS = max(1.0, float(os.getenv("KOALABYTE_EUCALYPTUS_SCAN_SECONDS", "3.0")))
SCAN_PAUSE_SECONDS = max(0.05, float(os.getenv("KOALABYTE_EUCALYPTUS_SCAN_PAUSE_SECONDS", "0.15")))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _read_pid() -> int | None:
    try:
        value = int(PID_PATH.read_text(encoding="utf-8").strip())
        return value if value > 1 else None
    except Exception:
        return None


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _status_payload(*, status: str, active: bool, pid: int | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "status": status,
        "active": bool(active),
        "pid": int(pid) if pid else None,
        "mode": "persistent_passive_ble_observation",
        "capture_path": str(CAPTURE_PATH),
        "scan_seconds": SCAN_SECONDS,
        "safety_scope": "passive BLE advertisement observation only; no pairing, connection, probing, disruption, spoofing, jamming, or access workflow",
        "updated_at": time.time(),
        **extra,
    }


def worker_status() -> dict[str, Any]:
    pid = _read_pid()
    active = _pid_alive(pid)
    if not active and PID_PATH.exists():
        PID_PATH.unlink(missing_ok=True)
    try:
        existing = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            existing = {}
    except Exception:
        existing = {}
    payload = dict(existing)
    payload.update(
        _status_payload(
            status="EUCALYPTUS_WORKER_ACTIVE" if active else "EUCALYPTUS_WORKER_STOPPED",
            active=active,
            pid=pid if active else None,
        )
    )
    return payload


def start_worker() -> dict[str, Any]:
    current = worker_status()
    if current.get("active"):
        current["status"] = "EUCALYPTUS_WORKER_ALREADY_ACTIVE"
        return current

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    stdout_handle = STDOUT_PATH.open("ab")
    stderr_handle = STDERR_PATH.open("ab")
    env = dict(os.environ)
    package_root = str(REPO_ROOT / "pi-companion")
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = package_root + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "koalablue.eucalyptus_persistent_worker", "worker"],
            cwd=str(REPO_ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        stdout_handle.close()
        stderr_handle.close()

    PID_PATH.write_text(f"{process.pid}\n", encoding="utf-8")
    payload = _status_payload(
        status="EUCALYPTUS_WORKER_STARTING",
        active=True,
        pid=process.pid,
        started_at=time.time(),
    )
    _atomic_json(STATUS_PATH, payload)
    time.sleep(0.2)
    if not _pid_alive(process.pid):
        PID_PATH.unlink(missing_ok=True)
        failed = worker_status()
        failed["status"] = "EUCALYPTUS_WORKER_START_FAILED"
        failed["active"] = False
        return failed
    payload["status"] = "EUCALYPTUS_WORKER_ACTIVE"
    _atomic_json(STATUS_PATH, payload)
    return payload


def stop_worker(timeout_seconds: float = 5.0) -> dict[str, Any]:
    pid = _read_pid()
    if not _pid_alive(pid):
        PID_PATH.unlink(missing_ok=True)
        payload = _status_payload(
            status="EUCALYPTUS_WORKER_ALREADY_STOPPED",
            active=False,
            stopped_at=time.time(),
        )
        _atomic_json(STATUS_PATH, payload)
        return payload

    assert pid is not None
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + max(0.5, timeout_seconds)
    while time.monotonic() < deadline and _pid_alive(pid):
        time.sleep(0.05)
    if _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    PID_PATH.unlink(missing_ok=True)
    payload = _status_payload(
        status="EUCALYPTUS_WORKER_STOPPED",
        active=False,
        stopped_at=time.time(),
        previous_pid=pid,
    )
    _atomic_json(STATUS_PATH, payload)
    return payload


def restart_worker() -> dict[str, Any]:
    previous = stop_worker()
    started = start_worker()
    started["restart"] = {
        "previous_status": previous.get("status"),
        "restarted_at": time.time(),
    }
    _atomic_json(STATUS_PATH, started)
    return started


async def _discover_once() -> list[dict[str, Any]]:
    from bleak import BleakScanner  # type: ignore

    try:
        found = await BleakScanner.discover(timeout=SCAN_SECONDS, return_adv=True)
    except TypeError:
        devices = await BleakScanner.discover(timeout=SCAN_SECONDS)
        found = {
            str(getattr(device, "address", "")): (device, None)
            for device in devices
        }

    rows: list[dict[str, Any]] = []
    now = time.time()
    for address, payload in found.items():
        if isinstance(payload, tuple):
            device = payload[0]
            adv = payload[1] if len(payload) > 1 else None
        else:
            device = payload
            adv = None
        resolved_address = str(getattr(device, "address", address) or address).strip()
        if not resolved_address:
            continue
        rows.append(
            {
                "type": "ble_adv_seen",
                "source": "eucalyptus-persistent-pi-ble",
                "address": resolved_address,
                "name": str(
                    getattr(device, "name", "")
                    or (getattr(adv, "local_name", "") if adv is not None else "")
                    or ""
                ).strip(),
                "rssi": getattr(adv, "rssi", None) if adv is not None else getattr(device, "rssi", None),
                "timestamp": now,
                "safety_scope": "passive BLE advertisement observation only",
            }
        )
    return rows


async def _worker_loop() -> int:
    stop_requested = False

    def _stop(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    pid = os.getpid()
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(f"{pid}\n", encoding="utf-8")
    total_records = 0
    scans = 0
    started_at = time.time()
    _atomic_json(
        STATUS_PATH,
        _status_payload(
            status="EUCALYPTUS_WORKER_ACTIVE",
            active=True,
            pid=pid,
            started_at=started_at,
            scans=scans,
            records=total_records,
        ),
    )

    try:
        while not stop_requested:
            try:
                rows = await _discover_once()
                scans += 1
                for row in rows:
                    append_jsonl(CAPTURE_PATH, row)
                total_records += len(rows)
                _atomic_json(
                    STATUS_PATH,
                    _status_payload(
                        status="EUCALYPTUS_WORKER_ACTIVE",
                        active=True,
                        pid=pid,
                        started_at=started_at,
                        scans=scans,
                        records=total_records,
                        last_scan_records=len(rows),
                        last_scan_at=time.time(),
                    ),
                )
            except Exception as exc:
                scans += 1
                _atomic_json(
                    STATUS_PATH,
                    _status_payload(
                        status="EUCALYPTUS_WORKER_SCAN_ERROR",
                        active=True,
                        pid=pid,
                        started_at=started_at,
                        scans=scans,
                        records=total_records,
                        error=str(exc)[:300],
                    ),
                )
                await asyncio.sleep(min(2.0, SCAN_PAUSE_SECONDS + 0.5))
                continue
            await asyncio.sleep(SCAN_PAUSE_SECONDS)
    finally:
        PID_PATH.unlink(missing_ok=True)
        _atomic_json(
            STATUS_PATH,
            _status_payload(
                status="EUCALYPTUS_WORKER_STOPPED",
                active=False,
                started_at=started_at,
                stopped_at=time.time(),
                scans=scans,
                records=total_records,
            ),
        )
    return 0


def install_eucalyptus_persistent_control() -> None:
    from . import eucalyptus_wigle

    original = eucalyptus_wigle.control_status
    if getattr(original, "_koalabyte_persistent_worker", False):
        return

    def control_status(action: str) -> dict[str, Any]:
        normalized = str(action or "status").strip().lower()
        if normalized == "start":
            return start_worker()
        if normalized == "stop":
            return stop_worker()
        if normalized == "restart":
            return restart_worker()
        result = original(action)
        if normalized == "status" and isinstance(result, dict):
            result = dict(result)
            result["persistent_worker"] = worker_status()
        return result

    control_status._koalabyte_persistent_worker = True  # type: ignore[attr-defined]
    eucalyptus_wigle.control_status = control_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Persistent passive Eucalyptus BLE worker")
    parser.add_argument("command", choices=("worker", "start", "stop", "restart", "status"))
    args = parser.parse_args()
    if args.command == "worker":
        try:
            return asyncio.run(_worker_loop())
        except KeyboardInterrupt:
            return 0
    if args.command == "start":
        payload = start_worker()
    elif args.command == "stop":
        payload = stop_worker()
    elif args.command == "restart":
        payload = restart_worker()
    else:
        payload = worker_status()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not str(payload.get("status", "")).endswith("FAILED") else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CAPTURE_PATH",
    "PID_PATH",
    "STATUS_PATH",
    "install_eucalyptus_persistent_control",
    "restart_worker",
    "start_worker",
    "stop_worker",
    "worker_status",
]
