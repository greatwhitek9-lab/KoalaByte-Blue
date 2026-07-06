from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

DISPLAY_NAME = "Vehicle Diagnostics Readiness"
DEFAULT_OUTPUT_DIR = Path("logs/vehicle_diagnostics")


def ensure_output_dir(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run(args: list[str], timeout: float = 4.0) -> dict[str, object]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return {"command": args, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
    except FileNotFoundError as exc:
        return {"command": args, "returncode": 127, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired:
        return {"command": args, "returncode": 124, "stdout": "", "stderr": "command timed out"}


def _serial_candidates() -> list[str]:
    candidates: list[str] = []
    for pattern in ["/dev/serial/by-id/*", "/dev/ttyUSB*", "/dev/ttyACM*"]:
        for path in sorted(Path("/").glob(pattern.removeprefix("/"))):
            candidates.append(str(Path("/") / path))
    return sorted(set(candidates))


def safety_scope() -> dict[str, object]:
    return {
        "mode": "vehicle_diagnostics_readiness_only",
        "allowed": [
            "Check whether an owner-authorized OBD-II diagnostic path appears to be available.",
            "Record adapter/software readiness to a local artifact.",
            "Document safe next steps for reading standard diagnostic data with an appropriate tool.",
        ],
        "not_performed": [
            "No diagnostic trouble code clearing or reset operation is sent.",
            "No actuator, brake, steering, lighting, lock, powertrain, immobilizer, coding, adaptation, or ECU programming action is sent.",
            "No arbitrary CAN frames, UDS security access, seed/key workflow, OEM-specific commands, or captured traffic replay are sent.",
        ],
        "operator_requirements": [
            "Use only on an owned or explicitly authorized vehicle.",
            "Resolve and document the underlying fault before using a separate commercial scan tool to clear codes.",
            "Do not use code clearing to hide a known defect, bypass emissions inspection, or mask safety-related warnings.",
        ],
    }


def readiness(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = ensure_output_dir(output_dir)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = root / f"vehicle_diagnostics_readiness_{stamp}.json"
    requested_port = os.getenv("KOALABYTE_OBD_PORT") or os.getenv("OBD_PORT") or "auto"
    python_obd_available = importlib.util.find_spec("obd") is not None
    serial_candidates = _serial_candidates()
    data: dict[str, Any] = {
        "display_name": DISPLAY_NAME,
        "action": "vehicle-diagnostics-readiness",
        "status": "VEHICLE_DIAGNOSTICS_READY" if python_obd_available and serial_candidates else "VEHICLE_DIAGNOSTICS_OPTIONAL_NOT_READY",
        "adapter_type": "ELM327-compatible OBD-II adapter recommended for vehicle diagnostics",
        "innomaker_can_note": "The InnoMaker USB-CAN kit remains optional and is kept for isolated bench CAN work, not direct vehicle diagnostics.",
        "requested_port": requested_port,
        "serial_candidates": serial_candidates,
        "python_obd_available": python_obd_available,
        "python3_obd_import_check": _run(["python3", "-c", "import obd; print('python-obd available')"]),
        "ip_can_links": _run(["bash", "-lc", "ip -details link show type can 2>/dev/null || true"]),
        "safety_scope": safety_scope(),
        "clear_codes_enabled": False,
        "clear_codes_note": "KoalaByte does not send code-clearing/reset commands from this action. Use a proper scan tool after repair and documentation.",
        "timestamp": time.time(),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data


def clear_codes_safety_note(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = ensure_output_dir(output_dir)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = root / f"clear_codes_safety_note_{stamp}.json"
    data: dict[str, Any] = {
        "display_name": "Clear Codes Safety Note",
        "action": "clear-codes-safety-note",
        "status": "CLEAR_CODES_NOT_AUTOMATED",
        "clear_codes_enabled": False,
        "reason": "Clearing diagnostic trouble codes is a reset/write operation that can mask unresolved safety or emissions faults.",
        "safe_workflow": [
            "Read and save the codes first.",
            "Repair or document the underlying issue.",
            "Confirm the vehicle is owned or explicitly authorized.",
            "Use a dedicated commercial scan tool or manufacturer-approved diagnostic workflow if clearing is appropriate.",
            "Road-test or re-check readiness monitors afterward where legally and mechanically appropriate.",
        ],
        "safety_scope": safety_scope(),
        "timestamp": time.time(),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    data["artifact_path"] = str(path)
    return data
