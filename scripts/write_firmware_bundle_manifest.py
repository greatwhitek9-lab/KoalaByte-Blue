#!/usr/bin/env python3
"""Validate KoalaByte firmware artifacts and write the canonical bundle manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_MANIFEST = ROOT / "version/koalabyte_protocol.json"
ESP32_RELEASE_PATCH = ROOT / "firmware/esp32-dualeye/scripts/patch_release_version.py"
T114_SOURCE = ROOT / "firmware/t114-combined-safe/src/main.c"

ESP32_LAYOUT = (
    ("bootloader.bin", 0x00000000, 0x00008000, 4 * 1024),
    ("partitions.bin", 0x00008000, 0x0000E000, 1024),
    ("boot_app0.bin", 0x0000E000, 0x00010000, 4 * 1024),
    ("firmware.bin", 0x00010000, 0x00CB0000, 64 * 1024),
    ("srmodels.bin", 0x00CB0000, 0x01000000, 256 * 1024),
)
T114_MIN_BYTES = 64 * 1024
UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
UF2_FAMILY_ID = 0x239A0071
UF2_BLOCK_BYTES = 512


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def required_text(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"required source contract is missing: {path}")
    return path.read_text(encoding="utf-8")


def extract_esp32_fw() -> str:
    text = required_text(ESP32_RELEASE_PATCH)
    match = re.search(
        r'^new\s*=\s*[\'\"]#define KOALABLUE_FW_VERSION \\"([^\"]+)\\"[\'\"]$',
        text,
        re.MULTILINE,
    )
    if not match:
        match = re.search(
            r'^new\s*=\s*[\'\"]#define KOALABLUE_FW_VERSION "([^"]+)"[\'\"]$',
            text,
            re.MULTILINE,
        )
    if not match:
        raise RuntimeError("unable to resolve stamped ESP32 firmware version")
    return match.group(1)


def extract_t114_fw() -> str:
    text = required_text(T114_SOURCE)
    match = re.search(r'^#define KOALA_FW "([^"]+)"$', text, re.MULTILINE)
    if not match:
        raise RuntimeError("unable to resolve T114 firmware version")
    return match.group(1)


def record(path: Path, bundle: Path, *, address: int | None = None) -> dict[str, object]:
    size = path.stat().st_size
    row: dict[str, object] = {
        "path": str(path.relative_to(bundle)),
        "bytes": size,
        "sha256": sha256(path),
    }
    if address is not None:
        row["flash_address"] = f"0x{address:08x}"
    return row


def require_binary_markers(data: bytes, markers: tuple[str, ...], label: str) -> None:
    missing = [marker for marker in markers if marker.encode("utf-8") not in data]
    if missing:
        raise RuntimeError(f"{label} is missing compiled identity markers: {missing}")


def decode_uf2_payload(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) % UF2_BLOCK_BYTES:
        raise RuntimeError(f"T114 UF2 size is not a multiple of 512 bytes: {len(raw)}")
    chunks: list[tuple[int, bytes]] = []
    expected_blocks: int | None = None
    seen_numbers: set[int] = set()
    for offset in range(0, len(raw), UF2_BLOCK_BYTES):
        block = raw[offset : offset + UF2_BLOCK_BYTES]
        start0, start1, flags, target, payload_size, number, total, family = struct.unpack_from(
            "<8I", block, 0
        )
        end_magic = struct.unpack_from("<I", block, 508)[0]
        if (start0, start1, end_magic) != (
            UF2_MAGIC_START0,
            UF2_MAGIC_START1,
            UF2_MAGIC_END,
        ):
            raise RuntimeError(f"invalid UF2 magic at block offset {offset}")
        if payload_size <= 0 or payload_size > 476:
            raise RuntimeError(f"invalid UF2 payload size {payload_size} at block {number}")
        if family != UF2_FAMILY_ID:
            raise RuntimeError(
                f"unexpected T114 UF2 family at block {number}: 0x{family:08x}"
            )
        if expected_blocks is None:
            expected_blocks = total
        elif total != expected_blocks:
            raise RuntimeError("inconsistent UF2 total block count")
        if number in seen_numbers:
            raise RuntimeError(f"duplicate UF2 block number: {number}")
        seen_numbers.add(number)
        chunks.append((target, block[32 : 32 + payload_size]))
    if expected_blocks is None or len(chunks) != expected_blocks:
        raise RuntimeError(
            f"incomplete UF2 block set: observed={len(chunks)} expected={expected_blocks}"
        )
    chunks.sort(key=lambda item: item[0])
    minimum = chunks[0][0]
    maximum = max(address + len(payload) for address, payload in chunks)
    if minimum != 0x00026000:
        raise RuntimeError(f"unexpected T114 UF2 minimum target: 0x{minimum:08x}")
    image = bytearray(b"\xff" * (maximum - minimum))
    for address, payload in chunks:
        start = address - minimum
        image[start : start + len(payload)] = payload
    return bytes(image)


def validate_esp32(
    bundle: Path,
    included: bool,
    *,
    fw: str,
    protocol: str,
    repo_protocol: str,
) -> list[dict[str, object]]:
    if not included:
        return []
    output: list[dict[str, object]] = []
    for name, start, end, minimum in ESP32_LAYOUT:
        path = bundle / "esp32" / name
        if not path.is_file():
            raise RuntimeError(f"missing ESP32 artifact: {path}")
        size = path.stat().st_size
        capacity = end - start
        if size < minimum:
            raise RuntimeError(
                f"ESP32 artifact is unexpectedly small: {name}={size} bytes, minimum={minimum}"
            )
        if size > capacity:
            raise RuntimeError(
                f"ESP32 artifact overlaps the next partition: {name}={size} bytes, capacity={capacity}"
            )
        output.append(record(path, bundle, address=start))
    require_binary_markers(
        (bundle / "esp32" / "firmware.bin").read_bytes(),
        ("esp32-s3-dualeye", fw, protocol, repo_protocol),
        "ESP32 application image",
    )
    return output


def validate_t114(
    bundle: Path,
    included: bool,
    *,
    fw: str,
    protocol: str,
    repo_protocol: str,
) -> dict[str, object] | None:
    if not included:
        return None
    path = bundle / "t114" / "koalabyte-t114-current.uf2"
    if not path.is_file():
        raise RuntimeError(f"missing T114 UF2 artifact: {path}")
    if path.stat().st_size < T114_MIN_BYTES:
        raise RuntimeError(
            f"T114 UF2 is unexpectedly small: {path.stat().st_size} bytes"
        )
    payload = decode_uf2_payload(path)
    require_binary_markers(
        payload,
        ("heltec-t114", "heltec_mouth_status", fw, protocol, repo_protocol),
        "T114 UF2 application payload",
    )
    return record(path, bundle)


def write_checksums(bundle: Path) -> None:
    rows = []
    for path in sorted(bundle.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            rows.append(f"{sha256(path)}  {path.relative_to(bundle)}")
    if not rows:
        raise RuntimeError("firmware bundle contains no files")
    (bundle / "SHA256SUMS.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--source-commit", default="unknown")
    parser.add_argument("--skip-esp32", action="store_true")
    parser.add_argument("--skip-t114", action="store_true")
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    bundle.mkdir(parents=True, exist_ok=True)
    protocol_manifest = json.loads(required_text(PROTOCOL_MANIFEST))
    repo_protocol = str(protocol_manifest["repo_protocol_version"])
    esp32_protocol = str(protocol_manifest["esp32_dualeye_min_protocol"])
    t114_protocol = str(protocol_manifest["heltec_t114_min_protocol"])
    esp32_fw = extract_esp32_fw()
    t114_fw = extract_t114_fw()
    esp32_files = validate_esp32(
        bundle,
        not args.skip_esp32,
        fw=esp32_fw,
        protocol=esp32_protocol,
        repo_protocol=repo_protocol,
    )
    t114_file = validate_t114(
        bundle,
        not args.skip_t114,
        fw=t114_fw,
        protocol=t114_protocol,
        repo_protocol=repo_protocol,
    )

    manifest = {
        "schema": 2,
        "bundle": "koalabyte-blue-current",
        "source_commit": args.source_commit,
        "built_at": time.time(),
        "dependencies_gated_before_build": True,
        "hardware_contract_checked": True,
        "protocol_contract_checked": True,
        "compiled_identity_markers_checked": True,
        "esp32": {
            "target": "Waveshare ESP32-S3 DualEye 1.28 non-touch",
            "included": not args.skip_esp32,
            "chip": "esp32s3",
            "flash_mode": "qio",
            "flash_frequency": "80m",
            "flash_size": "16MB",
            "runtime_identity": {
                "device": "esp32-s3-dualeye",
                "fw": esp32_fw,
                "protocol": esp32_protocol,
                "repo_protocol_version": repo_protocol,
            },
            "files": esp32_files,
        },
        "t114": {
            "target": "Heltec T114 / HT-n5262 nRF52840 UF2",
            "included": not args.skip_t114,
            "volume_label": "HT-n5262",
            "family_id": "0x239a0071",
            "application_offset": "0x00026000",
            "runtime_identity": {
                "device": "heltec-t114",
                "fw": t114_fw,
                "protocol": t114_protocol,
                "repo_protocol_version": repo_protocol,
            },
            "file": t114_file,
        },
    }
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_checksums(bundle)
    print(json.dumps({"status": "FIRMWARE_BUNDLE_VALIDATED", "manifest": manifest}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
