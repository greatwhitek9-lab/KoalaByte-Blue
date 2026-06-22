from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .menu_theme import render_terminal_eucalyptus_card

DEFAULT_OUTPUT_DIR = Path("logs/greatwhite")
MAX_CAPTURE_SECONDS = 120


@dataclass
class GreatwhiteResult:
    action: str
    status: str
    generated_at: float
    output_dir: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    safety: Dict[str, Any] = field(default_factory=dict)


def _which(tool: str) -> str:
    return shutil.which(tool) or ""


def _run(argv: List[str], timeout: int = 30) -> Dict[str, Any]:
    try:
        proc = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
        return {"argv": argv, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
    except Exception as exc:
        return {"argv": argv, "returncode": -1, "stdout": "", "stderr": str(exc)}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc), "path": str(path)}


def _base_safety() -> Dict[str, Any]:
    return {
        "authorized_lab_use_only": True,
        "default_capture_duration_seconds": 30,
        "max_capture_duration_seconds": MAX_CAPTURE_SECONDS,
        "capture_requires_explicit_interface": True,
        "capture_requires_confirm_owned_lab": True,
        "does_not_enable_monitor_mode": True,
        "does_not_transmit_packets": True,
        "stores_local_artifacts_only": True,
    }


def status(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> GreatwhiteResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    tshark = _which("tshark")
    wireshark = _which("wireshark")
    dumpcap = _which("dumpcap")
    extcap = _which("extcap")
    nrf_sniffer_status = _read_json(Path("logs/nrf_sniffer_ble_status.json"))
    checks: Dict[str, Any] = {
        "tools": {"tshark": tshark, "wireshark": wireshark, "dumpcap": dumpcap, "extcap": extcap},
        "versions": {},
        "interfaces": {},
        "nrf_sniffer_ble": nrf_sniffer_status,
    }
    if tshark:
        checks["versions"]["tshark"] = _run([tshark, "--version"], timeout=10)
        checks["interfaces"] = _run([tshark, "-D"], timeout=20)
    if wireshark:
        checks["versions"]["wireshark"] = _run([wireshark, "--version"], timeout=10)
    if dumpcap:
        checks["versions"]["dumpcap"] = _run([dumpcap, "--version"], timeout=10)
    ready = bool(tshark or wireshark)
    result = GreatwhiteResult("Greatwhite", "ready" if ready else "needs_setup", time.time(), str(root), {}, checks, _base_safety())
    path = root / "greatwhite_status.json"
    result.artifacts["status_json"] = str(path)
    _write_json(path, asdict(result))
    return result


def interfaces(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> GreatwhiteResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    tshark = _which("tshark")
    if not tshark:
        result = GreatwhiteResult("Greatwhite interfaces", "needs_setup", time.time(), str(root), details={"error": "tshark not found"}, safety=_base_safety())
    else:
        iface_result = _run([tshark, "-D"], timeout=20)
        result = GreatwhiteResult("Greatwhite interfaces", "ready" if iface_result["returncode"] == 0 else "error", time.time(), str(root), details={"interfaces": iface_result}, safety=_base_safety())
    path = root / "greatwhite_interfaces.json"
    result.artifacts["interfaces_json"] = str(path)
    _write_json(path, asdict(result))
    return result


def nrf_sniffer_status(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> GreatwhiteResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    nrf_status = _read_json(Path("logs/nrf_sniffer_ble_status.json"))
    iface = interfaces(root)
    result = GreatwhiteResult(
        "Greatwhite nRF Sniffer BLE status",
        str(nrf_status.get("status", "missing")) if nrf_status else "missing",
        time.time(),
        str(root),
        {"interfaces_json": iface.artifacts.get("interfaces_json", "")},
        {"nrf_sniffer_ble": nrf_status, "interfaces": iface.details},
        {**_base_safety(), "proprietary_package_redistributed": False, "sniffer_firmware_flash_is_separate_intentional_action": True},
    )
    path = root / "greatwhite_nrf_sniffer_status.json"
    result.artifacts["nrf_sniffer_status_json"] = str(path)
    _write_json(path, asdict(result))
    return result


def capture(interface: str, duration_seconds: int = 30, output_dir: str | Path = DEFAULT_OUTPUT_DIR, capture_filter: str = "", confirm_owned_lab: bool = False) -> GreatwhiteResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    if not interface:
        raise ValueError("Greatwhite capture requires --interface. Run 'interfaces' first and choose an owned lab interface.")
    if not confirm_owned_lab:
        raise ValueError("Greatwhite capture requires --confirm-owned-lab to acknowledge authorized lab use.")
    duration = max(1, min(int(duration_seconds), MAX_CAPTURE_SECONDS))
    tshark = _which("tshark")
    if not tshark:
        raise RuntimeError("tshark not found. Run flash_all or setup_system_packages.sh first.")
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    pcap_path = root / f"greatwhite_{timestamp}.pcapng"
    meta_path = root / f"greatwhite_{timestamp}.json"
    argv = [tshark, "-i", interface, "-a", f"duration:{duration}", "-w", str(pcap_path)]
    if capture_filter:
        argv.extend(["-f", capture_filter])
    run_result = _run(argv, timeout=duration + 30)
    result = GreatwhiteResult(
        "Greatwhite bounded capture",
        "complete" if run_result["returncode"] == 0 else "error",
        time.time(),
        str(root),
        {"pcapng": str(pcap_path), "metadata_json": str(meta_path)},
        {"interface": interface, "duration_seconds": duration, "capture_filter": capture_filter, "command": run_result},
        _base_safety(),
    )
    _write_json(meta_path, asdict(result))
    return result


def summarize_pcap(path: str | Path, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> GreatwhiteResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    pcap = Path(path)
    if not pcap.exists():
        raise FileNotFoundError(f"pcap file not found: {pcap}")
    tshark = _which("tshark")
    if not tshark:
        raise RuntimeError("tshark not found. Run flash_all or setup_system_packages.sh first.")
    summary = _run([tshark, "-r", str(pcap), "-q", "-z", "io,phs"], timeout=60)
    result = GreatwhiteResult("Greatwhite pcap summary", "complete" if summary["returncode"] == 0 else "error", time.time(), str(root), details={"pcap": str(pcap), "summary": summary}, safety={**_base_safety(), "offline_analysis_only": True})
    out = root / f"{pcap.stem}_summary.json"
    result.artifacts["summary_json"] = str(out)
    _write_json(out, asdict(result))
    return result


def render(result: GreatwhiteResult) -> str:
    rows = ["Greatwhite is the KoalaByte Blue Wireshark/tshark wrapper for authorized lab packet review.", f"Status: {result.status}"]
    if result.artifacts:
        for key, value in result.artifacts.items():
            rows.append(f"{key}: {value}")
    if result.action.lower().endswith("status") or result.action == "Greatwhite":
        tools = result.details.get("tools", {}) if isinstance(result.details, dict) else {}
        if tools:
            rows.append(f"tshark: {tools.get('tshark') or 'missing'}")
            rows.append(f"wireshark: {tools.get('wireshark') or 'missing'}")
            rows.append(f"dumpcap: {tools.get('dumpcap') or 'missing'}")
        nrf_status = result.details.get("nrf_sniffer_ble", {}) if isinstance(result.details, dict) else {}
        if nrf_status:
            rows.append(f"nRF Sniffer BLE: {nrf_status.get('status', 'unknown')}")
    rows.append("Capture is bounded and requires explicit --interface plus --confirm-owned-lab.")
    return render_terminal_eucalyptus_card("Greatwhite", rows, subtitle="Wireshark / tshark reef patrol")


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="Greatwhite Wireshark/tshark wrapper for KoalaByte Blue")
    sub = parser.add_subparsers(dest="command")
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    interfaces_parser = sub.add_parser("interfaces")
    interfaces_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    sniffer_parser = sub.add_parser("nrf-sniffer-status")
    sniffer_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--interface", required=True)
    capture_parser.add_argument("--duration-seconds", type=int, default=30)
    capture_parser.add_argument("--capture-filter", default="")
    capture_parser.add_argument("--confirm-owned-lab", action="store_true")
    capture_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("pcap")
    summary_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    command = args.command or "status"
    if command == "status":
        result = status(args.output_dir)
    elif command == "interfaces":
        result = interfaces(args.output_dir)
    elif command == "nrf-sniffer-status":
        result = nrf_sniffer_status(args.output_dir)
    elif command == "capture":
        result = capture(args.interface, args.duration_seconds, args.output_dir, args.capture_filter, args.confirm_owned_lab)
    elif command == "summary":
        result = summarize_pcap(args.pcap, args.output_dir)
    else:
        parser.error(f"unknown command: {command}")
        return 2
    print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
