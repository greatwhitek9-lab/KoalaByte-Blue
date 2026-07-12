from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

DISPLAY_NAME = "TwoCan Read-Only Tools"
SUBMENU_NAME = "twocan_read_only"
GROUP_NAME = "CAN Bench Tools"
OUTPUT_DIR = Path("logs/twocan_vehicle_diagnostics")
CAPTURE_DIR = OUTPUT_DIR / "captures"
STATUS_PATH = OUTPUT_DIR / "twocan_read_only_status.json"

# Explicitly read-only OBD-II services. Service 04 (clear), service 08
# (actuator control), UDS/security access, coding, and raw transmit are absent.
READ_ONLY_SERVICE_NAMES = {
    "ELM_VERSION",
    "ELM_VOLTAGE",
    "STATUS",
    "STATUS_DRIVE_CYCLE",
    "FREEZE_DTC",
    "GET_DTC",
    "GET_CURRENT_DTC",
    "VIN",
    "CALIBRATION_ID",
    "CVN",
    "RPM",
    "SPEED",
    "COOLANT_TEMP",
    "ENGINE_LOAD",
    "FUEL_STATUS",
    "INTAKE_PRESSURE",
    "INTAKE_TEMP",
    "MAF",
    "THROTTLE_POS",
    "FUEL_LEVEL",
    "CONTROL_MODULE_VOLTAGE",
    "RUN_TIME",
    "DISTANCE_W_MIL",
    "WARMUPS_SINCE_DTC_CLEAR",
    "DISTANCE_SINCE_DTC_CLEAR",
    "TIME_SINCE_DTC_CLEARED",
}
FORBIDDEN_COMMAND_NAMES = {
    "CLEAR_DTC",
    "CLEAR_CODES",
    "ACTUATOR_TEST",
    "SECURITY_ACCESS",
    "ECU_CODING",
    "RAW_FRAME_INJECTION",
    "CAPTURE_REPLAY",
}

TWOCAN_COMMANDS: tuple[str, ...] = (
    "twocan_full_read_only_report",
    "twocan_adapter_identity",
    "twocan_vehicle_identity",
    "twocan_stored_dtcs",
    "twocan_pending_dtcs",
    "twocan_permanent_dtcs",
    "twocan_freeze_frame",
    "twocan_readiness_monitors",
    "twocan_live_pid_snapshot",
    "twocan_live_pid_log_30s",
    "twocan_offline_capture_review",
    "twocan_repair_verification_checklist",
)

LIVE_PID_NAMES: tuple[str, ...] = (
    "RPM",
    "SPEED",
    "COOLANT_TEMP",
    "ENGINE_LOAD",
    "FUEL_STATUS",
    "INTAKE_PRESSURE",
    "INTAKE_TEMP",
    "MAF",
    "THROTTLE_POS",
    "FUEL_LEVEL",
    "CONTROL_MODULE_VOLTAGE",
    "RUN_TIME",
)

FREEZE_PID_NAMES: tuple[str, ...] = tuple(f"DTC_{name}" for name in (
    "RPM",
    "SPEED",
    "COOLANT_TEMP",
    "ENGINE_LOAD",
    "FUEL_STATUS",
    "INTAKE_PRESSURE",
    "INTAKE_TEMP",
    "MAF",
    "THROTTLE_POS",
    "FUEL_LEVEL",
    "CONTROL_MODULE_VOLTAGE",
))


def _menu_rows() -> list[dict[str, object]]:
    from .menu_catalog import _item

    return [
        _item(GROUP_NAME, "Run Full Read-Only Scan", "twocan_full_read_only_report", "Run all supported safe OBD-II reads and write one report"),
        _item(GROUP_NAME, "Adapter Identity", "twocan_adapter_identity", "Read ELM adapter version, voltage, port, and protocol"),
        _item(GROUP_NAME, "Vehicle VIN and Calibration", "twocan_vehicle_identity", "Read VIN, calibration ID, and CVN when supported"),
        _item(GROUP_NAME, "Stored DTC Report", "twocan_stored_dtcs", "Read confirmed emission-related diagnostic codes; no clearing"),
        _item(GROUP_NAME, "Pending DTC Report", "twocan_pending_dtcs", "Read current or last-drive-cycle pending diagnostic codes"),
        _item(GROUP_NAME, "Permanent DTC Report", "twocan_permanent_dtcs", "Read service 0A permanent emission-related codes"),
        _item(GROUP_NAME, "Freeze-Frame Snapshot", "twocan_freeze_frame", "Read the triggering DTC and supported freeze-frame PIDs"),
        _item(GROUP_NAME, "Readiness Monitors", "twocan_readiness_monitors", "Read monitor status since clear and this drive cycle"),
        _item(GROUP_NAME, "Live PID Snapshot", "twocan_live_pid_snapshot", "Read one bounded snapshot of supported standard live PIDs"),
        _item(GROUP_NAME, "Live PID Log 30 Seconds", "twocan_live_pid_log_30s", "Log supported standard live PIDs for a bounded interval"),
        _item(GROUP_NAME, "Offline CAN Capture Review", "twocan_offline_capture_review", "Summarize a saved capture without transmitting or replaying it"),
        _item(GROUP_NAME, "Repair Verification Checklist", "twocan_repair_verification_checklist", "Write a repair and post-repair verification checklist"),
        _item(GROUP_NAME, "Clear Codes Safety Note", "twocan_clear_codes_safety_note", "Write the safe workflow note; no reset command is sent"),
        _item("System / Companion", "Back to Koala Kan Kommander", "submenu:koala_kan", "Return to Koala Kan Kommander"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ]


def install_menu_catalog() -> None:
    """Install executable TwoCan read-only actions into the shared jungle menu."""
    from . import menu_catalog
    from .menu_catalog import _item

    koala_rows = menu_catalog.SUBMENU_ITEMS.setdefault("koala_kan", [])
    if not any(str(row.get("command", "")) == f"submenu:{SUBMENU_NAME}" for row in koala_rows):
        row = _item(GROUP_NAME, "TwoCan Read-Only Tools", f"submenu:{SUBMENU_NAME}", "Open executable read-only OBD-II and offline capture review tools")
        insert_at = next(
            (index + 1 for index, existing in enumerate(koala_rows) if str(existing.get("command", "")) == "twocan_vehicle_diagnostics"),
            len(koala_rows),
        )
        koala_rows.insert(insert_at, row)

    menu_catalog.SUBMENU_ITEMS[SUBMENU_NAME] = _menu_rows()

    if not getattr(menu_catalog, "_twocan_read_only_title_patch", False):
        original_submenu_title = menu_catalog.submenu_title

        def patched_submenu_title(menu_name: str) -> str:
            if menu_name == SUBMENU_NAME:
                return DISPLAY_NAME
            return original_submenu_title(menu_name)

        menu_catalog.submenu_title = patched_submenu_title
        menu_catalog._twocan_read_only_title_patch = True

    _install_action_runner_patch()


def _install_action_runner_patch() -> None:
    try:
        from . import menu_action_runner
    except Exception:
        return
    if getattr(menu_action_runner, "_twocan_read_only_action_patch", False):
        return
    original_runner = menu_action_runner.run_automated_menu_action

    def patched_runner(command: str, label: str = "", group: str = "") -> dict[str, Any]:
        if command in TWOCAN_COMMANDS:
            return run_twocan_menu_action(command, label, group)
        return original_runner(command, label, group)

    menu_action_runner.run_automated_menu_action = patched_runner
    menu_action_runner._twocan_read_only_action_patch = True


def _stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _write_json(stem: str, payload: dict[str, Any]) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload.setdefault("display_name", DISPLAY_NAME)
    payload.setdefault("read_only", True)
    payload.setdefault("clear_codes_enabled", False)
    payload.setdefault("raw_vehicle_transmit_enabled", False)
    payload.setdefault("captured_traffic_replay_enabled", False)
    payload.setdefault("updated_at", time.time())
    path = OUTPUT_DIR / f"{_stamp()}_{stem}.json"
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    STATUS_PATH.write_text(json.dumps({
        "status": payload.get("status"),
        "command": payload.get("command"),
        "artifact_path": str(path),
        "read_only": True,
        "updated_at": time.time(),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def _write_markdown(stem: str, body: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{_stamp()}_{stem}.md"
    path.write_text(body, encoding="utf-8")
    return str(path)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "magnitude") and hasattr(value, "units"):
        return {"value": _jsonable(value.magnitude), "units": str(value.units), "display": str(value)}
    if hasattr(value, "__dict__"):
        public = {key: _jsonable(item) for key, item in vars(value).items() if not key.startswith("_")}
        return public or str(value)
    return str(value)


def _response_payload(response: Any) -> dict[str, Any]:
    if response is None:
        return {"supported": False, "value": None, "message": "No response object"}
    is_null = False
    try:
        is_null = bool(response.is_null())
    except Exception:
        pass
    value = getattr(response, "value", None)
    return {
        "supported": not is_null,
        "is_null": is_null,
        "value": _jsonable(value),
        "unit": str(getattr(response, "unit", "") or ""),
        "messages": _jsonable(getattr(response, "messages", [])),
    }


def _port_setting() -> Optional[str]:
    raw = (os.getenv("KOALABYTE_OBD_PORT") or os.getenv("OBD_PORT") or "").strip()
    return None if raw.lower() in {"", "auto", "none"} else raw


def _connect() -> tuple[Any, Any, dict[str, Any]]:
    try:
        import obd  # type: ignore
    except Exception as exc:
        return None, None, {
            "connected": False,
            "status": "TWOCAN_PYTHON_OBD_UNAVAILABLE",
            "error": str(exc),
            "install_hint": "pip install obd>=0.7.3",
        }

    port = _port_setting()
    timeout = float(os.getenv("KOALABYTE_OBD_TIMEOUT", "30"))
    try:
        if port:
            connection = obd.OBD(portstr=port, fast=False, timeout=timeout)
        else:
            connection = obd.OBD(fast=False, timeout=timeout)
    except Exception as exc:
        return obd, None, {
            "connected": False,
            "status": "TWOCAN_ADAPTER_CONNECT_FAILED",
            "requested_port": port or "auto",
            "error": str(exc),
        }

    connected = bool(connection.is_connected())
    info = {
        "connected": connected,
        "status": "TWOCAN_ADAPTER_CONNECTED" if connected else "TWOCAN_ADAPTER_NOT_CONNECTED",
        "requested_port": port or "auto",
        "port_name": _safe_call(connection.port_name),
        "protocol_name": _safe_call(connection.protocol_name),
        "protocol_id": _safe_call(connection.protocol_id),
        "connection_status": str(_safe_call(connection.status)),
    }
    return obd, connection, info


def _safe_call(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        return {"error": str(exc)}


def _close(connection: Any) -> None:
    if connection is not None:
        try:
            connection.close()
        except Exception:
            pass


def _query_named(obd_module: Any, connection: Any, name: str, *, force: bool = False) -> dict[str, Any]:
    if name in FORBIDDEN_COMMAND_NAMES or name == "CLEAR_DTC":
        return {"name": name, "blocked": True, "reason": "write/reset/control command is outside TwoCan read-only scope"}
    if not (name in READ_ONLY_SERVICE_NAMES or name.startswith("DTC_")):
        return {"name": name, "blocked": True, "reason": "command is not on the explicit read-only allowlist"}
    command = getattr(obd_module.commands, name, None)
    if command is None:
        return {"name": name, "available": False, "reason": "python-OBD command is unavailable"}
    if not force:
        try:
            if not connection.supports(command):
                return {"name": name, "available": True, "supported_by_vehicle": False, "value": None}
        except Exception:
            pass
    try:
        response = connection.query(command, force=force)
        response_payload = _response_payload(response)
        return {"name": name, "available": True, "supported_by_vehicle": not bool(response_payload.get("is_null")), "response": response_payload}
    except Exception as exc:
        return {"name": name, "available": True, "supported_by_vehicle": False, "error": str(exc)}


def _query_permanent_dtcs(obd_module: Any, connection: Any) -> dict[str, Any]:
    try:
        from obd.OBDCommand import OBDCommand  # type: ignore
        from obd.decoders import dtc  # type: ignore
        from obd.protocols import ECU  # type: ignore

        command = OBDCommand("GET_PERMANENT_DTC", "Read permanent DTCs", b"0A", 0, dtc, ECU.ALL, False)
        response = connection.query(command, force=True)
        return {"name": "GET_PERMANENT_DTC", "service": "0A", "response": _response_payload(response)}
    except Exception as exc:
        return {"name": "GET_PERMANENT_DTC", "service": "0A", "error": str(exc)}


def adapter_identity() -> dict[str, Any]:
    obd_module, connection, link = _connect()
    payload: dict[str, Any] = {"status": "TWOCAN_ADAPTER_IDENTITY_READY", "command": "twocan_adapter_identity", "link": link, "queries": {}}
    try:
        if connection is not None:
            payload["queries"] = {
                "ELM_VERSION": _query_named(obd_module, connection, "ELM_VERSION", force=True),
                "ELM_VOLTAGE": _query_named(obd_module, connection, "ELM_VOLTAGE", force=True),
            }
    finally:
        _close(connection)
    payload["artifact_path"] = _write_json("adapter_identity", payload)
    return payload


def vehicle_identity() -> dict[str, Any]:
    obd_module, connection, link = _connect()
    payload: dict[str, Any] = {"status": "TWOCAN_VEHICLE_IDENTITY_READY", "command": "twocan_vehicle_identity", "link": link, "queries": {}}
    try:
        if connection is not None:
            payload["queries"] = {name: _query_named(obd_module, connection, name) for name in ("VIN", "CALIBRATION_ID", "CVN")}
    finally:
        _close(connection)
    payload["artifact_path"] = _write_json("vehicle_identity", payload)
    return payload


def dtc_report(kind: str) -> dict[str, Any]:
    command_map = {
        "stored": ("twocan_stored_dtcs", "GET_DTC"),
        "pending": ("twocan_pending_dtcs", "GET_CURRENT_DTC"),
        "permanent": ("twocan_permanent_dtcs", "GET_PERMANENT_DTC"),
    }
    if kind not in command_map:
        raise ValueError(f"unsupported DTC report kind: {kind}")
    menu_command, obd_command = command_map[kind]
    obd_module, connection, link = _connect()
    payload: dict[str, Any] = {
        "status": f"TWOCAN_{kind.upper()}_DTC_REPORT_READY",
        "command": menu_command,
        "dtc_kind": kind,
        "link": link,
        "clear_codes_enabled": False,
    }
    try:
        if connection is not None:
            payload["query"] = _query_permanent_dtcs(obd_module, connection) if kind == "permanent" else _query_named(obd_module, connection, obd_command, force=True)
        else:
            payload["query"] = {"name": obd_command, "skipped": True, "reason": "adapter not connected"}
    finally:
        _close(connection)
    payload["artifact_path"] = _write_json(f"{kind}_dtcs", payload)
    return payload


def freeze_frame_snapshot() -> dict[str, Any]:
    obd_module, connection, link = _connect()
    payload: dict[str, Any] = {"status": "TWOCAN_FREEZE_FRAME_READY", "command": "twocan_freeze_frame", "link": link, "trigger_dtc": None, "freeze_pids": {}}
    try:
        if connection is not None:
            payload["trigger_dtc"] = _query_named(obd_module, connection, "FREEZE_DTC")
            payload["freeze_pids"] = {name: _query_named(obd_module, connection, name) for name in FREEZE_PID_NAMES}
    finally:
        _close(connection)
    payload["artifact_path"] = _write_json("freeze_frame", payload)
    return payload


def readiness_monitors() -> dict[str, Any]:
    obd_module, connection, link = _connect()
    payload: dict[str, Any] = {"status": "TWOCAN_READINESS_MONITORS_READY", "command": "twocan_readiness_monitors", "link": link, "queries": {}}
    try:
        if connection is not None:
            payload["queries"] = {name: _query_named(obd_module, connection, name) for name in ("STATUS", "STATUS_DRIVE_CYCLE")}
    finally:
        _close(connection)
    payload["artifact_path"] = _write_json("readiness_monitors", payload)
    return payload


def live_pid_snapshot() -> dict[str, Any]:
    obd_module, connection, link = _connect()
    payload: dict[str, Any] = {"status": "TWOCAN_LIVE_PID_SNAPSHOT_READY", "command": "twocan_live_pid_snapshot", "link": link, "pids": {}}
    try:
        if connection is not None:
            payload["pids"] = {name: _query_named(obd_module, connection, name) for name in LIVE_PID_NAMES}
    finally:
        _close(connection)
    payload["artifact_path"] = _write_json("live_pid_snapshot", payload)
    return payload


def live_pid_log(duration_seconds: Optional[float] = None, interval_seconds: Optional[float] = None) -> dict[str, Any]:
    duration = max(1.0, min(float(duration_seconds if duration_seconds is not None else os.getenv("KOALABYTE_TWOCAN_LIVE_SECONDS", "30")), 300.0))
    interval = max(0.25, min(float(interval_seconds if interval_seconds is not None else os.getenv("KOALABYTE_TWOCAN_LIVE_INTERVAL", "1")), 10.0))
    obd_module, connection, link = _connect()
    samples: list[dict[str, Any]] = []
    started = time.time()
    try:
        if connection is not None:
            while time.time() - started < duration:
                sample_started = time.time()
                samples.append({
                    "timestamp": sample_started,
                    "elapsed_seconds": sample_started - started,
                    "pids": {name: _query_named(obd_module, connection, name) for name in LIVE_PID_NAMES},
                })
                remaining = interval - (time.time() - sample_started)
                if remaining > 0:
                    time.sleep(remaining)
    finally:
        _close(connection)
    payload: dict[str, Any] = {
        "status": "TWOCAN_LIVE_PID_LOG_READY",
        "command": "twocan_live_pid_log_30s",
        "link": link,
        "requested_duration_seconds": duration,
        "interval_seconds": interval,
        "actual_duration_seconds": time.time() - started,
        "sample_count": len(samples),
        "samples": samples,
    }
    payload["artifact_path"] = _write_json("live_pid_log", payload)
    return payload


def _capture_candidates() -> list[Path]:
    explicit = (os.getenv("KOALABYTE_TWOCAN_CAPTURE_PATH") or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return [path] if path.is_file() else []
    roots = [CAPTURE_DIR, Path("logs/koala_kan_kommander"), Path("logs/can")]
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in ("*.json", "*.log", "*.txt", "*.candump"):
            candidates.extend(path for path in root.rglob(pattern) if path.is_file() and "twocan_read_only" not in path.name)
    return sorted(set(candidates), key=lambda path: path.stat().st_mtime, reverse=True)


def _normalize_can_id(value: Any) -> str:
    if isinstance(value, int):
        return f"0x{value:X}"
    text = str(value or "").strip().upper()
    if not text:
        return "UNKNOWN"
    try:
        return f"0x{int(text, 16):X}"
    except ValueError:
        return text


def _frames_from_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if any(key in value for key in ("can_id", "can_id_hex", "arbitration_id")):
            yield value
        for child in value.values():
            yield from _frames_from_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _frames_from_json(child)


_CANDUMP_HASH = re.compile(r"(?:^|\s)(?P<iface>can\d+)\s+(?P<id>[0-9A-Fa-f]{3,8})#(?P<data>[0-9A-Fa-f]*)")
_CANDUMP_BRACKET = re.compile(r"(?:^|\s)(?P<iface>can\d+)\s+(?P<id>[0-9A-Fa-f]{3,8})\s+\[(?P<dlc>\d+)\]\s*(?P<data>(?:[0-9A-Fa-f]{2}\s*)*)")


def _frames_from_text(text: str) -> Iterable[dict[str, Any]]:
    for line in text.splitlines():
        match = _CANDUMP_HASH.search(line) or _CANDUMP_BRACKET.search(line)
        if not match:
            continue
        data = re.sub(r"\s+", "", match.groupdict().get("data") or "")
        yield {
            "interface": match.group("iface"),
            "can_id_hex": match.group("id"),
            "dlc": int(match.groupdict().get("dlc") or len(data) // 2),
            "data_hex": " ".join(data[index:index + 2] for index in range(0, len(data), 2)).upper(),
        }


def offline_capture_review() -> dict[str, Any]:
    candidates = _capture_candidates()
    if not candidates:
        payload: dict[str, Any] = {
            "status": "TWOCAN_CAPTURE_NOT_FOUND",
            "command": "twocan_offline_capture_review",
            "capture_path": None,
            "search_paths": [str(CAPTURE_DIR), "logs/koala_kan_kommander", "logs/can"],
            "set_path_hint": "Set KOALABYTE_TWOCAN_CAPTURE_PATH to a saved JSON, candump, log, or text capture.",
            "offline_only": True,
            "replay_performed": False,
        }
        payload["artifact_path"] = _write_json("offline_capture_review", payload)
        return payload

    path = candidates[0]
    frames: list[dict[str, Any]] = []
    parse_error: Optional[str] = None
    try:
        if path.suffix.lower() == ".json":
            frames = list(_frames_from_json(json.loads(path.read_text(encoding="utf-8", errors="ignore"))))
        else:
            frames = list(_frames_from_text(path.read_text(encoding="utf-8", errors="ignore")))
    except Exception as exc:
        parse_error = str(exc)

    ids = Counter(_normalize_can_id(frame.get("can_id_hex", frame.get("can_id", frame.get("arbitration_id")))) for frame in frames)
    dlcs = Counter(str(frame.get("dlc", "unknown")) for frame in frames)
    interfaces = Counter(str(frame.get("interface", "unknown")) for frame in frames)
    payload = {
        "status": "TWOCAN_OFFLINE_CAPTURE_REVIEW_READY" if parse_error is None else "TWOCAN_OFFLINE_CAPTURE_REVIEW_PARTIAL",
        "command": "twocan_offline_capture_review",
        "capture_path": str(path),
        "capture_size_bytes": path.stat().st_size,
        "frame_count": len(frames),
        "unique_can_ids": len(ids),
        "top_can_ids": ids.most_common(25),
        "dlc_counts": dict(dlcs),
        "interfaces": dict(interfaces),
        "parse_error": parse_error,
        "offline_only": True,
        "replay_performed": False,
        "raw_transmit_performed": False,
        "sample_frames": [_jsonable(frame) for frame in frames[:20]],
    }
    payload["artifact_path"] = _write_json("offline_capture_review", payload)
    return payload


def repair_verification_checklist() -> dict[str, Any]:
    body = """# TwoCan Repair Verification Checklist

## Before repair

- Confirm the vehicle is owned or explicitly authorized.
- Save stored, pending, and permanent DTC reports before changing anything.
- Save freeze-frame, readiness-monitor, VIN/calibration, and live-PID artifacts.
- Record symptoms, operating conditions, battery voltage, mileage, and recent work.

## Repair

- Diagnose the root cause using manufacturer service information and appropriate test equipment.
- Repair wiring, connectors, sensors, mechanical faults, or software only through approved procedures.
- Do not use KoalaByte for DTC clearing, ECU coding, actuator tests, security access, seed/key work, OEM raw-frame injection, or captured-traffic replay.

## Post-repair verification

- Re-read stored and pending codes without clearing them from KoalaByte.
- Compare live PIDs against the pre-repair artifact under the same safe operating conditions.
- Verify freeze-frame context and readiness status are consistent with the repair.
- Use a dedicated commercial or manufacturer-approved scan tool if a reset is appropriate.
- Complete a safe road test only when mechanically and legally appropriate.
- Re-run stored, pending, permanent, readiness, and live-PID reports after the drive cycle.
- Save the final artifacts with the repair order or maintenance record.
"""
    markdown_path = _write_markdown("repair_verification_checklist", body)
    payload: dict[str, Any] = {
        "status": "TWOCAN_REPAIR_VERIFICATION_CHECKLIST_READY",
        "command": "twocan_repair_verification_checklist",
        "checklist_path": markdown_path,
        "clear_codes_enabled": False,
        "operator_note": "Use a dedicated approved scan tool for any justified reset after the underlying fault is repaired and documented.",
    }
    payload["artifact_path"] = _write_json("repair_verification_checklist", payload)
    return payload


def full_read_only_report() -> dict[str, Any]:
    # Individual actions intentionally open/close their own connection so each
    # artifact is useful on its own and failures remain isolated.
    results = {
        "adapter_identity": adapter_identity(),
        "vehicle_identity": vehicle_identity(),
        "stored_dtcs": dtc_report("stored"),
        "pending_dtcs": dtc_report("pending"),
        "permanent_dtcs": dtc_report("permanent"),
        "freeze_frame": freeze_frame_snapshot(),
        "readiness_monitors": readiness_monitors(),
        "live_pid_snapshot": live_pid_snapshot(),
        "offline_capture_review": offline_capture_review(),
        "repair_verification_checklist": repair_verification_checklist(),
    }
    payload: dict[str, Any] = {
        "status": "TWOCAN_FULL_READ_ONLY_REPORT_READY",
        "command": "twocan_full_read_only_report",
        "results": results,
        "excluded": [
            "DTC clearing/reset",
            "ECU coding/adaptation/programming",
            "actuator/output tests",
            "UDS security access or seed/key workflows",
            "OEM raw frame injection",
            "captured traffic replay",
            "synthetic ECU/UDS simulators",
        ],
    }
    payload["artifact_path"] = _write_json("full_read_only_report", payload)
    return payload


def run_twocan_menu_action(command: str, label: str = "", group: str = "") -> dict[str, Any]:
    handlers: dict[str, Callable[[], dict[str, Any]]] = {
        "twocan_full_read_only_report": full_read_only_report,
        "twocan_adapter_identity": adapter_identity,
        "twocan_vehicle_identity": vehicle_identity,
        "twocan_stored_dtcs": lambda: dtc_report("stored"),
        "twocan_pending_dtcs": lambda: dtc_report("pending"),
        "twocan_permanent_dtcs": lambda: dtc_report("permanent"),
        "twocan_freeze_frame": freeze_frame_snapshot,
        "twocan_readiness_monitors": readiness_monitors,
        "twocan_live_pid_snapshot": live_pid_snapshot,
        "twocan_live_pid_log_30s": live_pid_log,
        "twocan_offline_capture_review": offline_capture_review,
        "twocan_repair_verification_checklist": repair_verification_checklist,
    }
    handler = handlers.get(command)
    if handler is None:
        return {"status": "TWOCAN_READ_ONLY_COMMAND_UNKNOWN", "command": command, "label": label, "group": group, "read_only": True}
    try:
        result = handler()
        result.setdefault("label", label)
        result.setdefault("group", group)
        result.setdefault("selected_from_menu", True)
        result.setdefault("voice_command_compatible", True)
        result.setdefault("touchscreen_compatible", True)
        result.setdefault("gpio_button_compatible", True)
        result.setdefault("keyboard_compatible", True)
        return result
    except Exception as exc:
        payload: dict[str, Any] = {
            "status": "TWOCAN_READ_ONLY_ACTION_FAILED",
            "command": command,
            "label": label,
            "group": group,
            "error": str(exc),
            "read_only": True,
        }
        payload["artifact_path"] = _write_json("action_failed", payload)
        return payload
