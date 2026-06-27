#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
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

STATUS_FILES = {
    "One-shot installer": "logs/one_shot_install_status.json",
    "Menu display sync": "logs/one_shot/menu_display_sync_status.json",
    "Control surface": "logs/one_shot/control_surface_status.json",
    "Doctor": "logs/doctor/koalabyte_doctor_status.json",
    "BlueZ helper": "logs/koala_bluez/gatttool_setup_status.json",
    "KillerKoala/Ollama": "logs/killerkoala/ollama_setup_status.json",
    "Menu current state": "logs/menu_sync/current_menu_state.json",
    "CAN optional": "logs/can/innomaker_optional_status.json",
    "Antenna readiness": "logs/koalabyte_external_antenna_status.json",
    "Safe mode": "logs/safe_mode/current_safe_mode.json",
}


def read_json(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.exists():
        return {"present": False, "path": relative}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload.setdefault("present", True)
            payload.setdefault("path", relative)
            return payload
        return {"present": True, "path": relative, "value": payload}
    except Exception as exc:
        return {"present": True, "path": relative, "error": str(exc), "size_bytes": path.stat().st_size}


def build_status() -> dict[str, Any]:
    return {
        "status": "KOALABYTE_STATUS_DASHBOARD_READY",
        "updated_at": time.time(),
        "repo_root": str(ROOT),
        "files": {name: read_json(relative) for name, relative in STATUS_FILES.items()},
    }


def render_html(payload: dict[str, Any]) -> str:
    cards = []
    for name, data in payload["files"].items():
        status = data.get("status", "missing" if not data.get("present") else "present")
        pretty = html.escape(json.dumps(data, indent=2, sort_keys=True))
        cards.append(f"<section><h2>{html.escape(name)} <span>{html.escape(str(status))}</span></h2><pre>{pretty}</pre></section>")
    return """<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>KoalaByte Blue Status</title>
<style>
body{margin:0;background:#020908;color:#e8ff9c;font-family:system-ui,Arial,sans-serif}header{padding:18px 22px;background:#071f12;border-bottom:4px solid #b8ff6b}h1{margin:0;color:#ffd63e;text-shadow:2px 2px #124c1d}main{padding:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}section{background:#0c3c1c;border:3px solid #ffaf31;border-radius:16px;padding:12px;box-shadow:0 0 0 2px #53ff68 inset}h2{margin:0 0 8px;color:#c9ff58}h2 span{font-size:.75em;color:#3ecfff}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#020908;border-radius:10px;padding:10px;color:#f2e15b}.hint{color:#b8ff6b}</style>
</head><body><header><h1>🌿 KoalaByte Blue Status</h1><div class='hint'>Local-only dashboard. Refresh to update.</div></header><main>""" + "".join(cards) + "</main></body></html>"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local KoalaByte Blue status dashboard")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--json", action="store_true", help="Print status JSON and exit")
    args = parser.parse_args()

    if args.json:
        print(json.dumps(build_status(), indent=2, sort_keys=True))
        return 0

    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse
        import uvicorn
    except Exception as exc:
        print(f"FastAPI/uvicorn unavailable: {exc}", file=sys.stderr)
        print(json.dumps(build_status(), indent=2, sort_keys=True))
        return 0

    app = FastAPI(title="KoalaByte Blue Status")

    @app.get("/api/status")
    def api_status():
        return JSONResponse(build_status())

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(render_html(build_status()))

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
