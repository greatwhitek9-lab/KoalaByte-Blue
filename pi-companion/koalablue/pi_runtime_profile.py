"""Hardware-aware runtime budgets for KoalaByte Blue Ultra.

This module is deliberately read-only: it detects the host and recommends safe
resource limits. It never changes clocks, voltage, firmware, GPIO wiring, or
system services.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any


def _read_text(paths: tuple[str, ...]) -> str:
    for raw in paths:
        try:
            value = Path(raw).read_text(encoding="utf-8", errors="ignore").strip("\x00\n ")
            if value:
                return value
        except OSError:
            pass
    return ""


def _memory_mib() -> int:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return max(1, int(line.split()[1]) // 1024)
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _cpu_count() -> int:
    return max(1, os.cpu_count() or 1)


def build_profile(model: str, memory_mib: int, cpu_count: int | None = None) -> dict[str, Any]:
    """Build deterministic settings, also used by hardware-free tests."""
    normalized = model.lower()
    is_pi = "raspberry pi" in normalized
    is_pi5 = is_pi and ("raspberry pi 5" in normalized or "raspberry pi 500" in normalized)
    is_pi4 = is_pi and ("raspberry pi 4" in normalized or "raspberry pi 400" in normalized)
    cpus = max(1, int(cpu_count or 1))
    memory = max(0, int(memory_mib))

    if is_pi5:
        generation = "pi5"
        if memory >= 7000:
            context, parallel, keep_alive, predict, fps, workers = 2048, 2, "300s", 160, 60, min(4, cpus)
        elif memory >= 3500:
            context, parallel, keep_alive, predict, fps, workers = 1536, 1, "120s", 128, 45, min(4, cpus)
        else:
            context, parallel, keep_alive, predict, fps, workers = 1024, 1, "60s", 96, 30, min(2, cpus)
    elif is_pi4:
        generation = "pi4"
        context, parallel, keep_alive, predict, fps, workers = (
            (1536, 1, "120s", 112, 30, min(3, cpus)) if memory >= 3500
            else (1024, 1, "60s", 80, 24, min(2, cpus))
        )
    elif is_pi:
        generation = "pi3_or_older"
        context, parallel, keep_alive, predict, fps, workers = 768, 1, "60s", 64, 20, 1
    else:
        generation = "generic_linux"
        context, parallel, keep_alive, predict, fps, workers = 1024, 1, "60s", 96, 30, min(2, cpus)

    return {
        "profile": generation,
        "model": model or "unknown",
        "is_raspberry_pi": is_pi,
        "is_pi5": is_pi5,
        "architecture": platform.machine(),
        "memory_mib": memory,
        "cpu_count": cpus,
        "ai": {
            "model": "killerkoala-tinyllama:latest",
            "context_length": context,
            "num_parallel": parallel,
            "max_loaded_models": 1,
            "keep_alive": keep_alive,
            "num_predict": predict,
            "reason": "conservative RAM-aware Ollama limits; user-provided environment overrides take precedence",
        },
        "display": {
            "hdmi_fps": fps,
            "koalagotchi_fps": fps,
            "backend": "auto_wayland_x11_or_kmsdrm",
            "serial_ownership": "unchanged_exclusive_services",
        },
        "processing": {
            "worker_budget": workers,
            "firmware_build_jobs": 1 if memory < 4096 else min(4, cpus),
            "build_swap_target_mib": 2048 if memory < 4096 else 1024,
            "thermal_policy": "observe_only_no_overclock",
        },
        "power": {
            "required_preflight": "vcgencmd get_throttled must parse; current/latched undervoltage blocks hardware writes",
            "recommended_pi5_supply": "official 27W USB-C / 5V 5A for full peripheral budget",
        } if is_pi5 else {
            "required_preflight": "vcgencmd get_throttled must parse; current/latched undervoltage blocks hardware writes"
        },
    }


def detect_profile() -> dict[str, Any]:
    model = _read_text(("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"))
    return build_profile(model, _memory_mib(), _cpu_count())
