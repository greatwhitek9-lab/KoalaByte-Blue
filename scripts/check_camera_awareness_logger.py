#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from koalablue.camera_awareness_logger import (
    append_observation,
    create_observation,
    export_csv,
    export_json,
    load_observations,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        obs = create_observation(
            label="Test public camera",
            camera_type="unknown camera",
            location_text="test intersection",
            confidence="low",
            visible_markings="visible pole tag",
            notes="Manual public observation only; no electronic probing performed.",
        )
        append_observation(obs, root)
        rows = load_observations(root)
        assert len(rows) == 1
        assert rows[0].local_asset_id.startswith("cam-")
        assert rows[0].observation_id.startswith("obs-")
        json_path = export_json(rows, root)
        csv_path = export_csv(rows, root)
        assert json.loads(json_path.read_text(encoding="utf-8"))[0]["label"] == "Test public camera"
        assert "Test public camera" in csv_path.read_text(encoding="utf-8")
        try:
            create_observation(label="bad", notes="MAC address 00:11:22:33:44:55")
        except ValueError:
            pass
        else:
            raise AssertionError("MAC-like values must be rejected")
    print("Camera awareness logger smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
