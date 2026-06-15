from __future__ import annotations

import asyncio
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from bleak import BleakScanner
except Exception:  # pragma: no cover - allows docs/tests on non-BLE hosts
    BleakScanner = None  # type: ignore


@dataclass
class UrbanPoachingConfig:
    """Config for the Urban Poaching authorized BLE fox-hunt game."""

    target_name: str = "KoalaByte Lab"
    target_address: Optional[str] = None
    scan_seconds: float = 4.0
    rounds: int = 12
    capture_radius_rssi: int = -48
    close_rssi: int = -60
    warm_rssi: int = -72
    log_dir: str = "logs/urban_poaching"
    xp_reward_found: int = 25
    xp_reward_round: int = 1
    authorized_only: bool = True


@dataclass
class HuntObservation:
    timestamp: float
    address: str
    name: str
    rssi: int
    tx_power: Optional[int] = None


@dataclass
class HuntRound:
    round_number: int
    timestamp: float
    best_rssi: Optional[int]
    smoothed_rssi: Optional[float]
    direction_hint: str
    distance_hint: str
    found: bool
    observations: List[HuntObservation] = field(default_factory=list)


@dataclass
class HuntResult:
    game: str
    target_name: str
    target_address: Optional[str]
    started_at: float
    ended_at: float
    status: str
    found: bool
    score: int
    xp_reward: int
    rounds: List[HuntRound]
    log_path: str


class UrbanPoachingGame:
    """RSSI-guided BLE fox-hunt game for owned/authorized lab beacons.

    The default target is the KoalaByte Lab beacon. This class does not connect,
    pair, write, or interact with devices. It only observes BLE advertisements
    and turns RSSI trend changes into game hints.
    """

    def __init__(self, config: Optional[UrbanPoachingConfig] = None) -> None:
        self.config = config or UrbanPoachingConfig()
        self.log_dir = Path(self.config.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    async def play(self) -> HuntResult:
        if BleakScanner is None:
            raise RuntimeError("bleak is not available; install requirements on the Raspberry Pi first")

        started = time.time()
        rounds: List[HuntRound] = []
        rssi_history: List[int] = []
        found = False

        for round_number in range(1, self.config.rounds + 1):
            observations = await self._scan_round()
            best = max((obs.rssi for obs in observations), default=None)
            if best is not None:
                rssi_history.append(best)
                rssi_history = rssi_history[-5:]
            smoothed = statistics.mean(rssi_history) if rssi_history else None
            distance_hint = self._distance_hint(smoothed)
            direction_hint = self._trend_hint(rssi_history)
            round_found = bool(smoothed is not None and smoothed >= self.config.capture_radius_rssi)
            found = found or round_found
            rounds.append(
                HuntRound(
                    round_number=round_number,
                    timestamp=time.time(),
                    best_rssi=best,
                    smoothed_rssi=smoothed,
                    direction_hint=direction_hint,
                    distance_hint=distance_hint,
                    found=round_found,
                    observations=observations,
                )
            )
            if round_found:
                break

        ended = time.time()
        score = self._score(rounds, found)
        xp = self.config.xp_reward_found if found else max(0, len(rounds) * self.config.xp_reward_round)
        status = "FOUND" if found else "TIMEOUT"
        log_path = self._write_result(started, ended, status, found, score, xp, rounds)
        return HuntResult(
            game="Urban Poaching",
            target_name=self.config.target_name,
            target_address=self.config.target_address,
            started_at=started,
            ended_at=ended,
            status=status,
            found=found,
            score=score,
            xp_reward=xp,
            rounds=rounds,
            log_path=str(log_path),
        )

    async def _scan_round(self) -> List[HuntObservation]:
        devices = await BleakScanner.discover(timeout=self.config.scan_seconds, return_adv=True)  # type: ignore[union-attr]
        observations: List[HuntObservation] = []
        for _, pair in devices.items():
            device, adv = pair
            name = device.name or adv.local_name or ""
            address = device.address
            if not self._matches_target(name=name, address=address):
                continue
            tx_power = getattr(adv, "tx_power", None)
            observations.append(
                HuntObservation(
                    timestamp=time.time(),
                    address=address,
                    name=name,
                    rssi=int(device.rssi),
                    tx_power=tx_power if isinstance(tx_power, int) else None,
                )
            )
        return sorted(observations, key=lambda obs: obs.rssi, reverse=True)

    def _matches_target(self, *, name: str, address: str) -> bool:
        if self.config.target_address and address.lower() == self.config.target_address.lower():
            return True
        return bool(self.config.target_name and self.config.target_name.lower() in name.lower())

    def _distance_hint(self, smoothed_rssi: Optional[float]) -> str:
        if smoothed_rssi is None:
            return "no signal - sweep slower, rotate, and check line of sight"
        if smoothed_rssi >= self.config.capture_radius_rssi:
            return "capture range - target is close"
        if smoothed_rssi >= self.config.close_rssi:
            return "hot - close range"
        if smoothed_rssi >= self.config.warm_rssi:
            return "warm - keep sweeping"
        return "cold - weak signal"

    def _trend_hint(self, history: Iterable[int]) -> str:
        values = list(history)
        if len(values) < 2:
            return "collecting baseline"
        delta = values[-1] - values[0]
        if delta >= 8:
            return "getting warmer - keep moving this way"
        if delta <= -8:
            return "getting colder - backtrack or rotate"
        return "steady signal - fan left/right and compare RSSI"

    def _score(self, rounds: List[HuntRound], found: bool) -> int:
        if not rounds:
            return 0
        if not found:
            return max(0, 50 - len(rounds) * 2)
        best = max((r.best_rssi for r in rounds if r.best_rssi is not None), default=-100)
        speed_bonus = max(0, (self.config.rounds - len(rounds)) * 5)
        signal_bonus = max(0, int(best + 100))
        return 100 + speed_bonus + signal_bonus

    def _write_result(self, started: float, ended: float, status: str, found: bool, score: int, xp: int, rounds: List[HuntRound]) -> Path:
        path = self.log_dir / f"urban_poaching_{int(started)}.json"
        payload = {
            "game": "Urban Poaching",
            "target_name": self.config.target_name,
            "target_address": self.config.target_address,
            "started_at": started,
            "ended_at": ended,
            "status": status,
            "found": found,
            "score": score,
            "xp_reward": xp,
            "rounds": [asdict(r) for r in rounds],
            "safety_scope": "owned devices / authorized lab beacons only",
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path


def run_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Urban Poaching authorized BLE fox-hunt game")
    parser.add_argument("--target-name", default="KoalaByte Lab", help="Owned/authorized BLE beacon name to hunt")
    parser.add_argument("--target-address", default=None, help="Optional exact BLE address for owned/authorized target")
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--scan-seconds", type=float, default=4.0)
    args = parser.parse_args()

    game = UrbanPoachingGame(
        UrbanPoachingConfig(
            target_name=args.target_name,
            target_address=args.target_address,
            rounds=args.rounds,
            scan_seconds=args.scan_seconds,
        )
    )
    result = asyncio.run(game.play())
    print(json.dumps({
        "game": result.game,
        "status": result.status,
        "found": result.found,
        "score": result.score,
        "xp_reward": result.xp_reward,
        "log_path": result.log_path,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
