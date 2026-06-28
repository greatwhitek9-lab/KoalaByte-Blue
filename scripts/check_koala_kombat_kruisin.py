#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.koala_kombat_kruisin import SurveyRecord, _wigle_row, control, status  # noqa: E402


def main() -> int:
    os.environ["KOALA_KOMBAT_FIXED_LAT"] = "39.0001"
    os.environ["KOALA_KOMBAT_FIXED_LON"] = "-76.0001"
    payload = status()
    assert payload["status"] == "KOALA_KOMBAT_KRUISIN_STATUS"
    assert payload["gps_fix_available"] is True
    gps = control("gps-status")
    assert gps["status"] == "KOALA_KOMBAT_GPS_READY"
    row = _wigle_row(SurveyRecord(radio="wifi", identifier="AA:BB:CC:DD:EE:FF", name="KoalaAP", rssi=-55, channel="6", latitude=39.0001, longitude=-76.0001, first_seen="2026-01-01T00:00:00Z"))
    assert row is not None
    assert row["MAC"] == "AA:BB:CC:DD:EE:FF"
    assert row["Type"] == "WIFI"
    print("Koala Kombat Kruisin smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
