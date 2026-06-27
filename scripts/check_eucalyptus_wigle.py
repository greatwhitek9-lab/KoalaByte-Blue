#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.eucalyptus_wigle import build_gps_trail, upload_to_wigle  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        captures = root / "captures"
        out = root / "out"
        captures.mkdir()
        (captures / "ble.jsonl").write_text(json.dumps({"address": "AA:BB:CC:DD:EE:FF", "name": "KoalaTest", "rssi": -55, "timestamp": 1782558237}) + "\n", encoding="utf-8")
        os.environ["KOALABYTE_EUCALYPTUS_FIXED_LAT"] = "39.0001"
        os.environ["KOALABYTE_EUCALYPTUS_FIXED_LON"] = "-76.0001"
        result = build_gps_trail(capture_dirs=[captures], output_dir=out, max_records=10)
        assert result.records_written == 1
        assert result.records_with_location == 1
        assert Path(result.output_jsonl_path).exists()
        assert Path(result.wigle_csv_path).exists()
        dry = upload_to_wigle(dry_run=True)
        assert dry["status"] in {"EUCALYPTUS_WIGLE_UPLOAD_DRY_RUN", "EUCALYPTUS_WIGLE_UPLOAD_BLOCKED"}
    print("Eucalyptus GPS/WiGLE smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
