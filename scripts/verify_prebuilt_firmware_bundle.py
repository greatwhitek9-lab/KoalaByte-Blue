#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "firmware" / "prebuilt" / "manifest.json"
DEFAULT_STATUS = ROOT / "logs" / "one_shot" / "prebuilt_firmware_status.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_entry(name: str, entry: dict[str, object], *, require: bool) -> dict[str, object]:
    relative = str(entry.get("file", ""))
    expected = str(entry.get("sha256", ""))
    path = ROOT / relative
    result: dict[str, object] = {
        "name": name,
        "file": relative,
        "exists": path.is_file(),
        "expected_sha256": expected,
        "required": require,
    }
    if not path.is_file():
        result["status"] = "MISSING_REQUIRED" if require else "MISSING_SOURCE_CHECKOUT_OK"
        return result
    actual = sha256(path)
    result["actual_sha256"] = actual
    if not expected or expected == "PENDING_RELEASE_WORKFLOW":
        result["status"] = "UNPINNED_HASH"
    elif actual != expected:
        result["status"] = "HASH_MISMATCH"
    else:
        result["status"] = "VERIFIED"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify bundled KoalaByte peripheral firmware")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--strict", action="store_true", help="require both prebuilt images and pinned hashes")
    parser.add_argument("--require-t114", action="store_true")
    parser.add_argument("--require-esp32", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    if not args.manifest.is_file():
        failures.append(f"manifest missing: {args.manifest}")
        manifest: dict[str, object] = {}
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    t114 = check_entry(
        "heltec_t114",
        dict(manifest.get("heltec_t114", {})),
        require=args.strict or args.require_t114,
    )
    esp32 = check_entry(
        "esp32_s3_dualeye",
        dict(manifest.get("esp32_s3_dualeye", {})),
        require=args.strict or args.require_esp32,
    )

    for result in (t114, esp32):
        status = str(result.get("status", ""))
        if status in {"MISSING_REQUIRED", "HASH_MISMATCH"}:
            failures.append(f"{result['name']}: {status}")
        if args.strict and status == "UNPINNED_HASH":
            failures.append(f"{result['name']}: UNPINNED_HASH")

    payload = {
        "status": "PREBUILT_FIRMWARE_VERIFIED" if not failures else "PREBUILT_FIRMWARE_ERROR",
        "bundle_version": manifest.get("bundle_version", "unknown"),
        "strict": args.strict,
        "heltec_t114": t114,
        "esp32_s3_dualeye": esp32,
        "innomaker_firmware_flash": False,
        "failures": failures,
        "updated_at": time.time(),
    }
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.status.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
