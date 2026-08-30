#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/one_shot_checkpoint.py"
INSTALLER = ROOT / "one-shot-install.sh"


def run(*args: str, cwd: Path | None = None, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(HELPER), *args],
        cwd=str(cwd or ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != expect:
        raise AssertionError(
            f"checkpoint command returned {result.returncode}, expected {expect}: {args}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    try:
        installer = INSTALLER.read_text(encoding="utf-8")
        required_markers = [
            "--resume",
            "--reset-progress",
            "install_checkpoint.json",
            "migrate-legacy",
            'stage_id}" != "source_validation"',
            "run_step firmware_deployment",
            "run_step runtime_verification",
            "run_step runtime_health",
            "rerun with --resume",
        ]
        missing = [marker for marker in required_markers if marker not in installer]
        if missing:
            failures.append(f"one-shot installer missing resume markers: {missing}")
    except Exception as exc:
        failures.append(f"could not inspect one-shot installer: {exc}")

    try:
        compile_result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(HELPER)],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if compile_result.returncode != 0:
            failures.append(f"checkpoint helper does not compile: {compile_result.stderr.strip()}")
    except Exception as exc:
        failures.append(f"checkpoint helper compile check failed: {exc}")

    profile = {
        "service_user": "koala-test",
        "skip_packages": False,
        "skip_audio": False,
        "skip_can": False,
        "skip_ai": False,
        "skip_music": False,
        "skip_firmware": False,
        "firmware_build_only": False,
        "use_existing_firmware_bundle": False,
        "cleanup_firmware_build_tools": True,
        "install_innomaker_can": "auto",
        "can_interface": "can0",
        "can_bitrate": "500000",
    }
    profile_json = json.dumps(profile, sort_keys=True)

    with tempfile.TemporaryDirectory(prefix="koalabyte-resume-check-") as temp:
        root = Path(temp)
        checkpoint = root / "logs/one_shot/install_checkpoint.json"

        try:
            run(
                "init",
                "--path", str(checkpoint),
                "--profile-json", profile_json,
                "--source-revision", "abc123",
            )
            run(
                "started",
                "--path", str(checkpoint),
                "--stage", "pi_prerequisites",
                "--label", "Pi prerequisites",
            )
            run(
                "complete",
                "--path", str(checkpoint),
                "--stage", "pi_prerequisites",
            )
            run(
                "is-complete",
                "--path", str(checkpoint),
                "--stage", "pi_prerequisites",
            )
            run(
                "is-complete",
                "--path", str(checkpoint),
                "--stage", "firmware_deployment",
                expect=1,
            )
        except Exception as exc:
            failures.append(f"basic checkpoint lifecycle failed: {exc}")

        try:
            mismatched = dict(profile)
            mismatched["skip_firmware"] = True
            result = run(
                "init",
                "--path", str(checkpoint),
                "--profile-json", json.dumps(mismatched, sort_keys=True),
                "--source-revision", "def456",
                expect=2,
            )
            if "resume profile differs" not in result.stderr:
                failures.append("profile mismatch did not explain why resume was rejected")
        except Exception as exc:
            failures.append(f"profile mismatch protection failed: {exc}")

        legacy_root = root / "legacy"
        legacy_checkpoint = legacy_root / "logs/one_shot/install_checkpoint.json"
        write_json(
            legacy_root / "logs/deployment/whole_system_deployment_status.json",
            {"status": "complete", "step": "complete"},
        )
        write_json(
            legacy_root / "logs/killerkoala/ollama_setup_status.json",
            {"status": "ok", "step": "killerkoala_ollama"},
        )
        write_json(
            legacy_root / "logs/music_player/mopidy_setup_status.json",
            {"status": "MOPIDY_PLAYER_READY"},
        )
        try:
            run(
                "migrate-legacy",
                "--path", str(legacy_checkpoint),
                "--profile-json", profile_json,
                "--source-revision", "legacy123",
                "--root", str(legacy_root),
            )
            state = json.loads(legacy_checkpoint.read_text(encoding="utf-8"))
            adopted = set(state.get("completed", []))
            expected = {"firmware_deployment", "tinyllama", "mopidy"}
            if not expected.issubset(adopted):
                failures.append(
                    f"legacy migration did not adopt expected expensive stages: {sorted(adopted)}"
                )
            if state.get("legacy_migration") is not True:
                failures.append("legacy migration checkpoint was not labeled as migrated")
        except Exception as exc:
            failures.append(f"legacy migration failed: {exc}")

    payload = {
        "status": "ONE_SHOT_RESUME_READY" if not failures else "ONE_SHOT_RESUME_INCOMPLETE",
        "checkpoint_helper": str(HELPER.relative_to(ROOT)),
        "checkpoint_path": "logs/one_shot/install_checkpoint.json",
        "resume_command": "bash one-shot-install.sh --resume",
        "reset_command": "bash one-shot-install.sh --reset-progress",
        "legacy_adoption": ["firmware_deployment", "tinyllama", "mopidy"],
        "source_validation_always_reruns": True,
        "profile_mismatch_fails_closed": True,
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
