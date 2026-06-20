#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from koalablue.eucalyptus_cyberpet import (
    ACTION_NAME,
    load_state,
    read_eucalyptus_stats,
    render_tamagotchi_screen,
    run_terminal,
    update_pet_state,
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
        state, delta, should_grumble, _mood = update_pet_state(state, stats, idle_seconds=180, branch_width=60)
        assert ACTION_NAME == "Eucalyptus Mode"
        assert delta == 0
        assert not should_grumble
        screen = render_tamagotchi_screen(state, stats, delta=0, width=72)
        assert "EUCALYPTUS MODE" in screen
        assert "KOALAGOTCHI" in screen
        assert "Eucalyptus passive Bluetooth scanner/logger" in screen
        hungry_state = state.__class__(
            contentment=50,
            total_observations_seen=2,
            last_observation_count=1,
            last_new_data_time=time.time(),
            direction=1,
            position=0,
            mood="patrolling",
            boomerang_throws=0,
            updated_at=time.time(),
        )
        hungry_state, new_delta, _grumble, new_mood = update_pet_state(hungry_state, stats, idle_seconds=180, branch_width=60)
        assert new_delta == 1
        assert hungry_state.contentment > 50
        assert "eating" in new_mood
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
        run_terminal(capture_dirs=[capture], state_path=state_path, event_log=event_log, once=True, tick_seconds=0.1)
        assert state_path.exists()
        assert json.loads(state_path.read_text(encoding="utf-8"))["contentment"] >= 0
    print("Eucalyptus cyberpet smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
