#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

MANIFEST = ROOT / "version" / "koalabyte_protocol.json"
STATUS_PATH = ROOT / "logs" / "version" / "koalabyte_version_handshake.json"


def read_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def query_serial(port: str, payload: dict[str, Any], *, timeout: float = 0.75) -> dict[str, Any]:
    if not port or not Path(port).exists():
        return {"port": port, "present": False, "queried": False}
    try:
        import serial  # type: ignore

        with serial.Serial(port, baudrate=int(os.getenv("SERIAL_BAUD", "115200")), timeout=timeout, write_timeout=0.25) as ser:
            ser.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
            ser.flush()
            line = ser.readline().decode("utf-8", errors="replace").strip()
        if line:
            try:
                return {"port": port, "present": True, "queried": True, "response": json.loads(line)}
            except Exception:
                return {"port": port, "present": True, "queried": True, "raw_response": line}
        return {"port": port, "present": True, "queried": True, "response": None}
    except Exception as exc:
        return {"port": port, "present": True, "queried": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check KoalaByte Pi/ESP32/Heltec protocol version handshake")
    parser.add_argument("--strict", action="store_true", help="Fail when configured ports are present but do not answer")
    parser.add_argument("--esp32-port", default=os.getenv("KOALABYTE_ESP32_FACE_PORT", os.getenv("ESP32_PORT", "/dev/koalabyte-esp32-dualeye")))
    parser.add_argument("--heltec-port", default=os.getenv("KOALABYTE_HELTEC_USB_PORT", os.getenv("HELTEC_PORT", "/dev/koalabyte-heltec")))
    parser.add_argument("--output", default=str(STATUS_PATH))
    args = parser.parse_args()

    manifest = read_manifest()
    request = {"type": "version_status", "request": "koalabyte_protocol", "repo_protocol_version": manifest["repo_protocol_version"]}
    esp32 = query_serial(args.esp32_port, request)
    heltec = query_serial(args.heltec_port, request)

    failures: list[str] = []
    if args.strict:
        for name, result in {"esp32": esp32, "heltec": heltec}.items():
            if result.get("present") and not result.get("queried"):
                failures.append(f"{name} port present but handshake failed")
            if result.get("present") and result.get("queried") and not (result.get("response") or result.get("raw_response")):
                failures.append(f"{name} port present but no version response")

    status = {
        "status": "KOALABYTE_VERSION_HANDSHAKE_READY" if not failures else "KOALABYTE_VERSION_HANDSHAKE_INCOMPLETE",
        "updated_at": time.time(),
        "manifest": manifest,
        "pi": {"protocol_version": manifest["repo_protocol_version"], "menu_sync_supported": True},
        "esp32": esp32,
        "heltec": heltec,
        "strict": args.strict,
        "failures": failures,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": status["status"], "output": str(output), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
