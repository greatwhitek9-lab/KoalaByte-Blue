#!/usr/bin/env python3
"""Hardware-free checks and reporting for KoalaByte Blue Ultra Pi profiles."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
sys.path.insert(0, str(PI_ROOT))

from koalablue.pi_runtime_profile import build_profile, detect_profile


def validate(profile: dict) -> list[str]:
    errors: list[str] = []
    ai = profile["ai"]
    display = profile["display"]
    processing = profile["processing"]
    if ai["context_length"] not in {768, 1024, 1536, 2048, 3072}:
        errors.append("AI context is outside the validated conservative tiers")
    if ai["num_parallel"] not in {1, 2}:
        errors.append("AI parallelism must remain at one or two requests")
    if ai["max_loaded_models"] != 1:
        errors.append("only one local model may be loaded at a time")
    if not 15 <= display["hdmi_fps"] <= 60:
        errors.append("HDMI frame rate must remain between 15 and 60 FPS")
    if display["koalagotchi_fps"] != display["hdmi_fps"]:
        errors.append("Koalagotchi and HDMI frame budgets must remain synchronized")
    if processing["worker_budget"] < 1 or processing["firmware_build_jobs"] < 1:
        errors.append("processing budgets must be positive")
    if profile["is_pi5"] and profile["profile"] != "pi5":
        errors.append("Pi 5 was not assigned the Pi 5 profile")
    if profile["is_pi5"]:
        expected_model = (
            "llama3.2:3b" if profile["memory_mib"] >= 7000
            else "qwen2.5:1.5b" if profile["memory_mib"] >= 3500
            else "tinyllama:1.1b"
        )
        if ai.get("base_model") != expected_model:
            errors.append(f"Pi 5 model mismatch for {profile['memory_mib']} MiB: {ai.get('base_model')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="Run simulated profiles without writing a report")
    parser.add_argument("--json", action="store_true", help="Print the detected profile as JSON")
    parser.add_argument("--write-report", action="store_true", help="Write the detected hardware profile to logs/pi_hardware/pi5_ultra_profile.json")
    args = parser.parse_args()

    fixtures = [
        ("Raspberry Pi 5 Model B Rev 1.0", 2048, "pi5", 1024, 30, 1),
        ("Raspberry Pi 5 Model B Rev 1.0", 4096, "pi5", 1536, 45, 1),
        ("Raspberry Pi 5 Model B Rev 1.0", 8192, "pi5", 2048, 60, 1),
        ("Raspberry Pi 5 Model B Rev 1.0", 16384, "pi5", 3072, 60, 1),
        ("Raspberry Pi 3 Model B Plus Rev 1.3", 1024, "pi3_or_older", 768, 20, 1),
    ]
    failures = []
    for model, memory, expected_generation, expected_context, expected_fps, expected_parallel in fixtures:
        candidate = build_profile(model, memory, 4)
        failures.extend(validate(candidate))
        if candidate["profile"] != expected_generation:
            failures.append(f"profile mismatch for {model}/{memory} MiB")
        if candidate["ai"]["context_length"] != expected_context:
            failures.append(f"context mismatch for {model}/{memory} MiB")
        if candidate["display"]["hdmi_fps"] != expected_fps:
            failures.append(f"display FPS mismatch for {model}/{memory} MiB")
        if candidate["ai"]["num_parallel"] != expected_parallel:
            failures.append(f"parallelism mismatch for {model}/{memory} MiB")

    detected = detect_profile()
    failures.extend(validate(detected))
    report = {
        "status": "PI5_ULTRA_PROFILE_PASS" if not failures else "PI5_ULTRA_PROFILE_FAIL",
        "detected_profile": detected,
        "simulated_profiles_checked": len(fixtures),
        "failures": failures,
        "updated_at": time.time(),
    }
    if args.write_report:
        path = ROOT / "logs/pi_hardware/pi5_ultra_profile.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["report_path"] = str(path)
    if args.json or args.write_report:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["status"])
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        print(f"Detected profile: {detected['profile']} / {detected['memory_mib']} MiB RAM")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
