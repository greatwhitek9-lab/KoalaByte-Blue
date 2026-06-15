from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional


RANK_NOOB = "Noob"
RANK_HACKER = "Hacker"
RANK_LEGEND = "Legend"


@dataclass(frozen=True)
class KillerKoalaVoiceProfile:
    name: str = "killerkoala"
    accent: str = "Australian male"
    attitude: str = "edgy, gruff, cyberpunk lab companion"
    safe_scope: str = "authorized lab guidance, local diagnostics, status reactions, and defensive workflow narration"
    tts_voice_hint: str = "en-AU male, low pitch, gravelly delivery, confident but not hostile"


@dataclass(frozen=True)
class KillerKoalaLine:
    event: str
    rank: str
    text: str
    intensity: int
    tags: List[str]


@dataclass
class KillerKoalaState:
    xp: int = 0
    rank: str = RANK_NOOB
    confidence: int = 1
    selected_event: str = "status"
    selected_text: str = ""
    timestamp: float = 0.0


def rank_for_xp(xp: int) -> str:
    if xp >= 250:
        return RANK_LEGEND
    if xp >= 75:
        return RANK_HACKER
    return RANK_NOOB


def confidence_for_rank(rank: str) -> int:
    if rank == RANK_LEGEND:
        return 3
    if rank == RANK_HACKER:
        return 2
    return 1


VOCABULARY: Mapping[str, Mapping[str, List[str]]] = {
    "boot": {
        RANK_NOOB: [
            "Oi. killerkoala online. Keep it tidy, mate. Lab rules first.",
            "Booted and breathing. I am rough around the edges, but I am watching the board.",
            "Systems up. No cowboy nonsense, just clean signals and clean logs.",
        ],
        RANK_HACKER: [
            "killerkoala is up. The rig is humming and I am feeling sharper, mate.",
            "Blue is awake. Let us stalk the lab spectrum like we own the canopy.",
            "Boot clean. I have got the scent now; give me a target in scope.",
        ],
        RANK_LEGEND: [
            "killerkoala online. The bush is quiet because it knows I am awake.",
            "Blue is alive, mate. I am not checking the lab anymore; I am running it.",
            "Legend stack is hot. Give me the next move and try to keep up.",
        ],
    },
    "scan_start": {
        RANK_NOOB: [
            "Starting a clean scan. Eyes open, paws off anything out of scope.",
            "Scanning now. I will sniff the air and keep the claws tucked in.",
        ],
        RANK_HACKER: [
            "Scan rolling. Let us see what is lurking in the gum trees.",
            "Sweeping the local air. If it chirps, I will log it.",
        ],
        RANK_LEGEND: [
            "Scan is live. The spectrum is about to confess, mate.",
            "I am sweeping the canopy. Nothing squeaks without me hearing it.",
        ],
    },
    "scan_complete": {
        RANK_NOOB: [
            "Scan done. Logs are ready for a calm look.",
            "Finished the sweep. Nothing gets touched without permission.",
        ],
        RANK_HACKER: [
            "Sweep complete. I bagged the signals and left no mess.",
            "Scan wrapped. The log pile is looking useful, mate.",
        ],
        RANK_LEGEND: [
            "Scan complete. The air tried to hide things. Cute.",
            "Done. The whole canopy is mapped like it owes me rent.",
        ],
    },
    "device_found": {
        RANK_NOOB: [
            "New device spotted. Mark it, do not poke it.",
            "Signal found. We log first and ask permission before anything deeper.",
        ],
        RANK_HACKER: [
            "Fresh signal in the branches. I have tagged it for review.",
            "Device spotted. Looks chatty enough to write down.",
        ],
        RANK_LEGEND: [
            "Found one. It walked into my range like it had a death wish for privacy theater.",
            "New signal logged. It blinked, I saw it, end of story.",
        ],
    },
    "capture_saved": {
        RANK_NOOB: [
            "Capture saved. Good work, mate. Keep your notes clean.",
            "Saved the metadata. That is how we build a proper lab trail.",
        ],
        RANK_HACKER: [
            "Capture tucked away. Nice clean pouch of evidence.",
            "Saved it. That packet trail is starting to smell useful.",
        ],
        RANK_LEGEND: [
            "Capture saved. Beautiful. The lab record just got teeth.",
            "Logged and locked. I could find this trail in a cyclone.",
        ],
    },
    "error": {
        RANK_NOOB: [
            "Something coughed. Check the adapter, permissions, and cables.",
            "That did not land clean. No panic; verify the basics first.",
        ],
        RANK_HACKER: [
            "Tool barked at us. Check the stack and we will bite back properly.",
            "That command tripped. Logs first, ego later.",
        ],
        RANK_LEGEND: [
            "Error hit. Annoying, not fatal. Show me the log and I will skin it.",
            "Something broke. Fine. Broken things talk when you squeeze the logs.",
        ],
    },
    "level_up": {
        RANK_NOOB: [
            "XP gained. You are still a joey, but you are learning.",
            "Level ticked upward. Keep stacking clean wins.",
        ],
        RANK_HACKER: [
            "Level up. Now you are moving like you know the terrain.",
            "XP landed. Not bad, mate. The claws are getting sharper.",
        ],
        RANK_LEGEND: [
            "Legend status confirmed. I knew you had it in you. Mostly because I carried you.",
            "Level maxed. The lab should be nervous in a respectful way.",
        ],
    },
    "bluez_status": {
        RANK_NOOB: [
            "Checking BlueZ status. Adapter first, drama later.",
            "BlueZ check running. I will see if the radio stack is awake.",
        ],
        RANK_HACKER: [
            "BlueZ status pass. Let us see if the local stack is behaving.",
            "Checking the controller guts. No fluff, just facts.",
        ],
        RANK_LEGEND: [
            "BlueZ audit running. If the stack blinks wrong, I will know.",
            "Controller status check. The radio stack answers to me now.",
        ],
    },
    "ear_tag_tx_lab": {
        RANK_NOOB: [
            "Ear Tag TX Lab is synthetic only. Clean beacon, clean conscience.",
            "Starting lab beacon notes. Fresh payloads only, no replay rubbish.",
        ],
        RANK_HACKER: [
            "Ear Tag TX Lab ready. Synthetic signal, owned board, tidy test.",
            "That beacon is ours, mate. Watch the sequence and mind the logs.",
        ],
        RANK_LEGEND: [
            "Ear Tag TX Lab is hot. Synthetic, labeled, and cleaner than a lab coat at sunrise.",
            "Beacon workflow ready. The signal has a name, a leash, and a purpose.",
        ],
    },
    "koala_kry": {
        RANK_NOOB: [
            "Koala Kry is offline replay. We test the workflow, not the neighborhood.",
            "Replaying metadata locally. Safe, boring, useful. That is the point.",
        ],
        RANK_HACKER: [
            "Koala Kry is chewing through saved metadata. No RF mess, just clean replay.",
            "Offline replay running. The lab ghosts are dancing in a jar.",
        ],
        RANK_LEGEND: [
            "Koala Kry is live offline. I can make old metadata useful without making dumb noise.",
            "Replay pipeline engaged. The past is working for us now, mate.",
        ],
    },
    "shutdown": {
        RANK_NOOB: [
            "Shutting down. Save your logs and do not yank power like a galah.",
            "Powering down clean. Good labs end clean.",
        ],
        RANK_HACKER: [
            "Shutdown path armed. Logs tucked, claws in.",
            "Going dark. Leave the kit better than you found it.",
        ],
        RANK_LEGEND: [
            "Shutting down. The lab gets to breathe again.",
            "Going dark, mate. Try not to miss my charm too much.",
        ],
    },
    "inquiry_status": {
        RANK_NOOB: [
            "I am online, learning, and keeping it scoped.",
            "Status is steady. Still a bit scrappy, but useful.",
        ],
        RANK_HACKER: [
            "I am sharp, awake, and ready to work the lab.",
            "Status is solid. Give me a task and I will make it tidy.",
        ],
        RANK_LEGEND: [
            "I am operating at legend confidence. The lab is basically my backyard.",
            "Status is dangerous-looking but well behaved. My favorite setting.",
        ],
    },
    "inquiry_help": {
        RANK_NOOB: [
            "Ask for scan, status, logs, BlueZ, Ear Tag, Koala Kapture, or Koala Kry.",
            "I can help with safe lab scans, captures, reports, and local adapter checks.",
        ],
        RANK_HACKER: [
            "Give me scan, BlueZ status, monitor, capture, replay, report, or Ear Tag TX Lab.",
            "I can drive the lab flow: observe, log, summarize, and keep the mess contained.",
        ],
        RANK_LEGEND: [
            "Ask cleanly and I will run the lab like a machine: scan, log, monitor, report, repeat.",
            "I handle the safe workflow. You bring scope. I bring teeth.",
        ],
    },
}


ALIASES: Mapping[str, str] = {
    "status": "inquiry_status",
    "help": "inquiry_help",
    "scan": "scan_start",
    "bluez": "bluez_status",
    "capture": "capture_saved",
    "kapture": "capture_saved",
    "kry": "koala_kry",
    "ear_tag": "ear_tag_tx_lab",
    "shutdown_confirm": "shutdown",
}


def normalize_event(event: str) -> str:
    event = event.strip().lower().replace(" ", "_").replace("-", "_")
    return ALIASES.get(event, event)


def line_for_event(event: str, xp: int = 0, seed: Optional[int] = None) -> KillerKoalaState:
    normalized = normalize_event(event)
    rank = rank_for_xp(xp)
    confidence = confidence_for_rank(rank)
    rank_lines = VOCABULARY.get(normalized, VOCABULARY["inquiry_status"])
    candidates = rank_lines.get(rank) or rank_lines[RANK_NOOB]
    rng = random.Random(seed if seed is not None else int(time.time() * 1000))
    selected = rng.choice(candidates)
    return KillerKoalaState(
        xp=xp,
        rank=rank,
        confidence=confidence,
        selected_event=normalized,
        selected_text=selected,
        timestamp=time.time(),
    )


def vocabulary_manifest() -> Dict[str, object]:
    return {
        "voice_profile": asdict(KillerKoalaVoiceProfile()),
        "ranks": {
            RANK_NOOB: {"min_xp": 0, "confidence": 1},
            RANK_HACKER: {"min_xp": 75, "confidence": 2},
            RANK_LEGEND: {"min_xp": 250, "confidence": 3},
        },
        "events": sorted(VOCABULARY.keys()),
        "aliases": dict(ALIASES),
    }


def write_vocabulary_manifest(output_dir: str | Path = "logs/killerkoala") -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    out = root / "killerkoala_vocabulary_manifest.json"
    out.write_text(json.dumps(vocabulary_manifest(), indent=2, sort_keys=True), encoding="utf-8")
    return out


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="killerkoala companion vocabulary preview")
    parser.add_argument("event", nargs="?", default="status", help="Event or inquiry name")
    parser.add_argument("--xp", type=int, default=0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--manifest", action="store_true", help="Write vocabulary manifest")
    parser.add_argument("--output-dir", default="logs/killerkoala")
    args = parser.parse_args()

    if args.manifest:
        path = write_vocabulary_manifest(args.output_dir)
        print(json.dumps({"manifest_path": str(path)}, indent=2, sort_keys=True))
        return 0

    state = line_for_event(args.event, xp=args.xp, seed=args.seed)
    print(json.dumps(asdict(state), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
