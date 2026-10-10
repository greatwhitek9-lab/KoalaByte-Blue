"""Hardware-aware runtime tuning for KoalaByte Blue Ultra.

This module only detects the host and recommends bounded defaults. It does not
change power settings, flash firmware, or modify system configuration.
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any


def _read_model() -> str:
    for path in (
        Path("/proc/device-tree/model"),
        Path("/sys/firmware/devicetree/base/model"),
    ):
        try:
            value = path.read_bytes().decode("utf-8", errors="ignore").strip("\x00\n ")
            if value:
                return value
        except OSError:
            pass
    return "unknown"


def _memory_mib() -> int:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def detect_hardware_profile() -> dict[str, Any]:
    model = _read_model()
    model_lower = model.lower()
    memory_mib = _memory_mib()
    is_pi5 = "raspberry pi 5" in model_lower
    is_pi = "raspberry pi" in model_lower
    is_pi5_8gb = is_pi5 and memory_mib >= 7000

    if is_pi5_8gb:
        name = "pi5-8gb-ultra"
        ollama_context = 2048
        ollama_parallel = 2
        ollama_keep_alive = "5m"
        hdmi_fps = 45
        processing_workers = max(2, min(os.cpu_count() or 4, 4))
    elif is_pi5:
        name = "pi5-ultra"
        ollama_context = 1536
        ollama_parallel = 1
        ollama_keep_alive = "2m"
        hdmi_fps = 40
        processing_workers = max(2, min(os.cpu_count() or 4, 4))
    elif is_pi:
        name = "legacy-pi-safe"
        ollama_context = 768
        ollama_parallel = 1
        ollama_keep_alive = "60s"
        hdmi_fps = 30
        processing_workers = 1
    else:
        name = "generic-linux"
        ollama_context = 1024
        ollama_parallel = 1
        ollama_keep_alive = "2m"
        hdmi_fps = 30
        processing_workers = max(1, min(os.cpu_count() or 2, 4))

    return {
        "profile": name,
        "model": model,
        "is_raspberry_pi": is_pi,
        "is_pi5": is_pi5,
        "is_pi5_8gb": is_pi5_8gb,
        "architecture": platform.machine(),
        "memory_mib": memory_mib,
        "cpu_count": os.cpu_count() or 1,
        "processing_workers": processing_workers,
        "ollama": {
            "context_length": ollama_context,
            "parallel_requests": ollama_parallel,
            "max_loaded_models": 1,
            "keep_alive": ollama_keep_alive,
        },
        "hdmi": {"target_fps": hdmi_fps, "max_fps": 60},
        "notes": [
            "Recommendations only; existing explicit environment overrides take precedence.",
            "No firmware flashing or system configuration changes are performed by detection.",
        ],
    }


def profile_json() -> str:
    return json.dumps(detect_hardware_profile(), indent=2, sort_keys=True)
