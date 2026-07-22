#!/usr/bin/env python3
"""Verify the complete KoalaByte firmware bundle before flashing or cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "version/koalabyte_protocol.json"
EXPECTED_ESP32_FILES = {
    "bootloader.bin": (0x00000000, 0x00008000, 4 * 1024),
    "partitions.bin": (0x00008000, 0x0000E000, 1024),
    "boot_app0.bin": (0x0000E000, 0x00010000, 4 * 1024),
    "firmware.bin": (0x00010000, 0x00CB0000, 64 * 1024),
    "srmodels.bin": (0x00CB0000, 0x01000000, 256 * 1024),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"missing JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def verify_checksums(bundle: Path) -> int:
    checksum_path = bundle / "SHA256SUMS.txt"
    if not checksum_path.is_file():
        raise RuntimeError("firmware bundle is missing SHA256SUMS.txt")
    checked = 0
    for line_number, raw in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise RuntimeError(f"invalid checksum row {line_number}: {raw!r}")
        expected, relative = parts
        path = (bundle / relative).resolve()
        try:
            path.relative_to(bundle.resolve())
        except ValueError as exc:
            raise RuntimeError(f"checksum path escapes bundle: {relative}") from exc
        if not path.is_file():
            raise RuntimeError(f"checksummed file is missing: {relative}")
        actual = digest(path)
        if actual != expected.lower():
            raise RuntimeError(
                f"checksum mismatch for {relative}: expected={expected.lower()} actual={actual}"
            )
        checked += 1
    if checked < 2:
        raise RuntimeError("firmware bundle checksum list is unexpectedly short")
    return checked


def verify_identity(manifest: dict[str, object], protocol: dict[str, object]) -> None:
    if int(manifest.get("schema", 0)) < 2:
        raise RuntimeError("firmware bundle manifest predates exact runtime identity checks")
    esp32 = manifest.get("esp32")
    t114 = manifest.get("t114")
    if not isinstance(esp32, dict) or not isinstance(t114, dict):
        raise RuntimeError("firmware bundle manifest is missing board sections")
    esp_identity = esp32.get("runtime_identity")
    t114_identity = t114.get("runtime_identity")
    if not isinstance(esp_identity, dict) or not isinstance(t114_identity, dict):
        raise RuntimeError("firmware bundle manifest is missing runtime identities")
    expected = {
        "esp32": {
            "device": "esp32-s3-dualeye",
            "protocol": str(protocol["esp32_dualeye_min_protocol"]),
            "repo_protocol_version": str(protocol["repo_protocol_version"]),
        },
        "t114": {
            "device": "heltec-t114",
            "protocol": str(protocol["heltec_t114_min_protocol"]),
            "repo_protocol_version": str(protocol["repo_protocol_version"]),
        },
    }
    for board, identity in (("esp32", esp_identity), ("t114", t114_identity)):
        for key, wanted in expected[board].items():
            if str(identity.get(key) or "") != wanted:
                raise RuntimeError(
                    f"{board} bundle identity mismatch for {key}: "
                    f"expected={wanted!r} observed={identity.get(key)!r}"
                )
        if not str(identity.get("fw") or "").strip():
            raise RuntimeError(f"{board} bundle identity has no firmware version")


def verify_esp32(bundle: Path, manifest: dict[str, object]) -> None:
    section = manifest["esp32"]
    assert isinstance(section, dict)
    if not bool(section.get("included")):
        raise RuntimeError("ESP32 firmware is not included in this bundle")
    listed = section.get("files")
    if not isinstance(listed, list):
        raise RuntimeError("ESP32 manifest file list is missing")
    by_name = {
        Path(str(item.get("path") or "")).name: item
        for item in listed
        if isinstance(item, dict)
    }
    for name, (start, end, minimum) in EXPECTED_ESP32_FILES.items():
        path = bundle / "esp32" / name
        if not path.is_file():
            raise RuntimeError(f"missing ESP32 artifact: {name}")
        size = path.stat().st_size
        if size < minimum or size > end - start:
            raise RuntimeError(
                f"ESP32 artifact size violates partition bounds: {name}={size}, "
                f"minimum={minimum}, capacity={end-start}"
            )
        row = by_name.get(name)
        if not isinstance(row, dict):
            raise RuntimeError(f"ESP32 artifact is absent from manifest: {name}")
        if str(row.get("flash_address") or "").lower() != f"0x{start:08x}":
            raise RuntimeError(f"ESP32 manifest has wrong flash address for {name}")
        if int(row.get("bytes") or 0) != size or str(row.get("sha256") or "") != digest(path):
            raise RuntimeError(f"ESP32 manifest metadata does not match {name}")


def verify_t114(bundle: Path, manifest: dict[str, object]) -> None:
    section = manifest["t114"]
    assert isinstance(section, dict)
    if not bool(section.get("included")):
        raise RuntimeError("T114 firmware is not included in this bundle")
    path = bundle / "t114" / "koalabyte-t114-current.uf2"
    if not path.is_file() or path.stat().st_size < 64 * 1024:
        raise RuntimeError("T114 UF2 is missing or unexpectedly small")
    row = section.get("file")
    if not isinstance(row, dict):
        raise RuntimeError("T114 artifact metadata is missing")
    if int(row.get("bytes") or 0) != path.stat().st_size:
        raise RuntimeError("T114 manifest size does not match UF2")
    if str(row.get("sha256") or "") != digest(path):
        raise RuntimeError("T114 manifest checksum does not match UF2")
    if str(section.get("family_id") or "").lower() != "0x239a0071":
        raise RuntimeError("T114 UF2 family ID contract changed")
    if str(section.get("application_offset") or "").lower() != "0x00026000":
        raise RuntimeError("T114 application offset contract changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, default=ROOT / "releases/koalabyte-blue-current")
    parser.add_argument("--require", choices=("all", "esp32", "t114"), default="all")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        raise RuntimeError(f"firmware bundle directory is missing: {bundle}")
    manifest = load_json(bundle / "manifest.json")
    protocol = load_json(PROTOCOL_PATH)
    verify_identity(manifest, protocol)
    checked = verify_checksums(bundle)
    if args.require in {"all", "esp32"}:
        verify_esp32(bundle, manifest)
    if args.require in {"all", "t114"}:
        verify_t114(bundle, manifest)
    print(
        json.dumps(
            {
                "status": "FIRMWARE_BUNDLE_READY",
                "bundle": str(bundle),
                "required": args.require,
                "checksums_verified": checked,
                "source_commit": manifest.get("source_commit"),
                "esp32_identity": manifest["esp32"]["runtime_identity"],
                "t114_identity": manifest["t114"]["runtime_identity"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
