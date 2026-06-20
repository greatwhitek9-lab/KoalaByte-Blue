#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from koalablue.boomerang import (
    ACTION_NAME,
    KILLERKOALA_BOOMERANG_ALERTS,
    XP_REWARD_PER_LOG,
    award_boomerang_xp,
    speak_killerkoala_alert,
)
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
        xp_path = root / "xp_state.json"
        alert_log = root / "boomerang_alerts.jsonl"
        obs = create_observation(
            label="Test public camera",
            camera_type="unknown camera",
            location_text="test intersection",
            confidence="low",
            visible_markings="visible pole tag",
            notes="Manual public observation only; no electronic probing performed.",
        )
        append_observation(obs, root)
        start_line = speak_killerkoala_alert("boomerang_start", context={"log_root": str(root)}, alert_log=alert_log, tts_enabled=False)
        camera_line = speak_killerkoala_alert("camera_found", context={"camera_label": obs.label, "local_asset_id": obs.local_asset_id}, alert_log=alert_log, tts_enabled=False)
        before, after, rank = award_boomerang_xp(xp_path=xp_path)
        xp_line = speak_killerkoala_alert("xp_gain", context={"xp_reward": XP_REWARD_PER_LOG, "xp_after": after, "rank": rank}, alert_log=alert_log, tts_enabled=False)
        assert "Boomerang is live" in start_line
        assert "Camera found" in camera_line
        assert "Plus 10 XP" in xp_line
        alerts = [json.loads(line) for line in alert_log.read_text(encoding="utf-8").splitlines()]
        assert [row["event"] for row in alerts] == ["boomerang_start", "camera_found", "xp_gain"]
        assert "boomerang_start" in KILLERKOALA_BOOMERANG_ALERTS
        assert "camera_found" in KILLERKOALA_BOOMERANG_ALERTS
        assert "xp_gain" in KILLERKOALA_BOOMERANG_ALERTS
        assert before == 0
        assert after == XP_REWARD_PER_LOG
        assert rank == "Noob"
        xp_state = json.loads(xp_path.read_text(encoding="utf-8"))
        assert xp_state["last_module"] == ACTION_NAME
        assert xp_state["boomerang_logs"] == 1
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
    print("Camera awareness logger smoke check passed. Boomerang XP reward check passed. KillerKoala verbal alerts check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
