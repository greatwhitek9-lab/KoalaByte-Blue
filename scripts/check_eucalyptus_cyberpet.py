#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from koalablue.eucalyptus_cyberpet import (
    ACTION_NAME,
    read_eucalyptus_stats,
    render_tamagotchi_screen,
    run_interactive,
    update_pet_state,
    load_state,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        capture = root / "captures"
        capture.mkdir()
        (capture / "observations.jsonl").write_text('{"name":"demo"}\n{"name":"demo2"}\n', encoding="utf-8")
        stats = read_eucalyptus_stats([capture])
        assert stats.observation_count == 2
        state_path = root / "state.json"
        event_log = root / "events.jsonl"
        state = load_state(state_path, stats)
        state, delta, should_grumble, mood = update_pet_state(state, stats, idle_seconds=180, branch_width=60)
        assert ACTION_NAME == "Eucalyptus CyberPet"
        assert delta == 0
        assert not should_grumble
        screen = render_tamagotchi_screen(state, stats, delta=0, width=72)
        assert "EUCALYPTUS CYBERPET" in screen
        assert "passive Eucalyptus log watcher" in screen
        idle_state = state.__class__(
            contentment=50,
            total_observations_seen=2,
            last_observation_count=2,
            last_new_data_time=time.time() - 181,
            direction=1,
            position=0,
            mood="patrolling",
            boomerang_throws=0,
            updated_at=time.time(),
        )
        idle_state, _delta, grumble, _mood = update_pet_state(idle_state, stats, idle_seconds=180, branch_width=60)
        assert grumble
        assert idle_state.mood == "cranky boomerang toss"
        assert idle_state.boomerang_throws == 1
        run_interactive(capture_dirs=[capture], state_path=state_path, event_log=event_log, once=True, tick_seconds=0.1)
        assert state_path.exists()
        assert json.loads(state_path.read_text(encoding="utf-8"))["contentment"] >= 0
    print("Eucalyptus cyberpet smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
