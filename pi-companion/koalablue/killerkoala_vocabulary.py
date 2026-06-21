from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence


RANK_NOOB = "Noob"
RANK_HACKER = "Hacker"
RANK_LEGEND = "Legend"
DEFAULT_HISTORY_PATH = Path("logs/killerkoala/killerkoala_phrase_history.json")
RECENT_HISTORY_WINDOW = 24


@dataclass(frozen=True)
class KillerKoalaVoiceProfile:
    name: str = "killerkoala"
    accent: str = "Australian male"
    attitude: str = "gruff, cheeky, cyberpunk lab companion with legal-scope discipline"
    safe_scope: str = "authorized lab guidance, local diagnostics, status reactions, defensive workflow narration, XP, and menu guidance"
    tts_voice_hint: str = "en-AU male, low pitch, gravelly delivery, confident but not hostile"
    companion_architecture: str = "ESP32-S3 voice front end plus Raspberry Pi large-vocabulary companion engine"
    anti_repeat_policy: str = "avoid recently used lines per event/rank and rotate through generated Aussie/cyberpunk variants"


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


AUSSIE_TERMS: Sequence[str] = (
    "mate", "no dramas", "too easy", "righto", "give it a squiz", "suss it out", "fair dinkum",
    "strewth", "crikey", "bonza", "deadset", "heaps", "arvo", "reckon", "she'll be right",
    "chuffed", "keen as mustard", "chockers", "dodgy", "tidy", "good on ya", "bush telegraph",
    "gumtrees", "billabong", "dropbear", "joey", "roo", "wombat", "galah", "eucalyptus",
)

OPENERS: Mapping[str, Sequence[str]] = {
    RANK_NOOB: (
        "Righto, mate",
        "No dramas",
        "Too easy",
        "Give it a squiz",
        "Steady on",
        "All good",
        "Fair dinkum",
        "Good on ya",
        "Easy does it",
        "Keep it tidy",
    ),
    RANK_HACKER: (
        "Too easy, mate",
        "Righto, let's suss it out",
        "No dramas, I am on it",
        "Bonza, the rig is awake",
        "Deadset, I have got this",
        "Give me a tick",
        "The bush telegraph is talking",
        "Keen as mustard",
        "Heaps of signal in the scrub",
        "Clean as a whistle",
    ),
    RANK_LEGEND: (
        "Too easy, legend",
        "Deadset, the canopy is mine",
        "No dramas, I have already sniffed the wind",
        "Fair dinkum, this rig is humming",
        "The bush telegraph reports to me now",
        "Strewth, that was almost too neat",
        "Crikey, the lab is behaving for once",
        "Bonza work, mate",
        "I reckon the signals know my name",
        "She'll be right, because I am watching it",
    ),
}

EVENT_TAILS: Mapping[str, Mapping[str, Sequence[str]]] = {
    "boot": {
        RANK_NOOB: (
            "KillerKoala is online and keeping the paws inside the lab boundary.",
            "I am awake, scrappy, and ready to keep the gear honest.",
            "Boot is clean; cables, scope, and logs come first.",
            "The eyes are up and the lab rules are loaded.",
            "I am breathing electrons and watching the board.",
            "The little blue beast is awake; keep it legal and tidy.",
        ),
        RANK_HACKER: (
            "KillerKoala is up and the lab stack is starting to purr.",
            "The gumtree is wired, the logs are ready, and I am feeling sharper.",
            "Boot clean; give me scoped work and I will make it neat.",
            "Blue is awake and the canopy has my attention.",
            "The companion brain is warmed up and ready for a proper squiz.",
            "The rig is humming like a ute on a cold morning.",
        ),
        RANK_LEGEND: (
            "KillerKoala is online; the lab just got a foreman with teeth and manners.",
            "Blue is alive, the stack is quiet, and the signals know to behave.",
            "Legend mode is awake; give me clean scope and I will make the work sing.",
            "The canopy is mapped in my head before you even ask.",
            "The lab has a heartbeat and I am the grumpy little metronome.",
            "Everything is up; try not to look impressed, mate.",
        ),
    },
    "scan_start": {
        RANK_NOOB: (
            "starting a bounded scan and keeping the claws tucked in.",
            "checking the air without poking anything out of scope.",
            "listening only; good labs observe before they act.",
            "running a safe sweep and writing down what chirps.",
            "taking a careful look through the eucalyptus.",
            "watching the local radio chatter like a quiet joey.",
        ),
        RANK_HACKER: (
            "sweeping the local air and keeping the log pile tidy.",
            "running the discovery sweep; if it chirps, I will tag it.",
            "checking the canopy for friendly signals and lab beacons.",
            "sniffing the gumtrees with safe defaults on.",
            "putting the controller to work, clean and bounded.",
            "listening to the bush telegraph without making a racket.",
        ),
        RANK_LEGEND: (
            "sweeping the canopy like it owes us a proper inventory.",
            "running the scan; the spectrum can whisper, but it cannot mumble.",
            "taking a clean bite out of the local signal fog.",
            "mapping the air with manners, scope, and a bit of swagger.",
            "turning radio noise into a tidy lab record.",
            "checking the scrub; nothing squeaks without me noticing.",
        ),
    },
    "scan_complete": {
        RANK_NOOB: (
            "scan finished and the logs are ready for a calm look.",
            "sweep complete; no funny business, just clean notes.",
            "the air check is done and the pouch has the records.",
            "finished listening; review before touching anything deeper.",
            "the scan wrapped without drama.",
            "results are saved; now we think before we click.",
        ),
        RANK_HACKER: (
            "sweep complete and the signal pouch is looking useful.",
            "logs are packed, sorted, and ready for a proper squiz.",
            "scan wrapped; the canopy coughed up a few notes.",
            "finished clean; that is how you keep the lab respectable.",
            "radio sweep done, no mess left behind.",
            "the local chatter is logged and behaving.",
        ),
        RANK_LEGEND: (
            "scan complete; the spectrum tried to be coy and failed.",
            "the canopy is logged like it signed the paperwork itself.",
            "finished; I turned the air into evidence with manners.",
            "sweep done, tidy as a fresh workbench.",
            "the radio scrub has been read, filed, and mildly judged.",
            "done; even the quiet bits look accounted for.",
        ),
    },
    "device_found": {
        RANK_NOOB: (
            "new signal spotted; mark it, do not poke it.",
            "device seen; log first, permissions before anything deeper.",
            "fresh chirp in the scrub; keep the notes clean.",
            "signal found and tucked into the record.",
            "something spoke; we heard it and stayed polite.",
            "new device in view; scope check before curiosity.",
        ),
        RANK_HACKER: (
            "fresh signal in the branches; tagged for review.",
            "device spotted and logged like a proper field note.",
            "something chatty wandered into range; I wrote it down.",
            "new chirp in the gumtrees; it is in the pouch now.",
            "signal acquired, calm and scoped.",
            "the canopy blinked; I saw it.",
        ),
        RANK_LEGEND: (
            "new signal logged; it blinked, I saw it, end of story.",
            "fresh device in range; the record already knows its shape.",
            "something wandered through the scrub and met the clipboard.",
            "signal caught clean; no drama, no noise, no nonsense.",
            "the air twitched and I filed the twitch.",
            "new beacon noted with the efficiency of a grumpy park ranger.",
        ),
    },
    "capture_saved": {
        RANK_NOOB: (
            "capture saved; that is a clean little lab trail.",
            "metadata tucked away; tidy notes make tidy reports.",
            "saved it; good labs keep receipts.",
            "capture written without drama.",
            "the pouch has the packet notes.",
            "record saved; now we review it properly.",
        ),
        RANK_HACKER: (
            "capture tucked away; nice clean pouch of evidence.",
            "saved it; that packet trail is starting to smell useful.",
            "metadata logged, labelled, and ready for a squiz.",
            "clean capture saved; no noise, no mucking about.",
            "that record is chockers with useful bits.",
            "capture done; the report will not be starving.",
        ),
        RANK_LEGEND: (
            "capture saved; the lab record just grew teeth and a tail.",
            "logged and locked; I could find this trail in a cyclone.",
            "metadata stored like it paid rent in the evidence pouch.",
            "capture is clean, labelled, and smugly complete.",
            "the packet trail is dressed up and ready for review.",
            "saved; even future you will understand this one.",
        ),
    },
    "error": {
        RANK_NOOB: (
            "something coughed; check the adapter, permissions, and cables.",
            "that did not land clean; verify the basics first.",
            "tool tripped; logs before panic.",
            "a bit of static in the workflow; we can tidy it.",
            "the gear had a wobble; check power and paths.",
            "not fatal, just cranky.",
        ),
        RANK_HACKER: (
            "tool barked at us; check the stack and we will sort it properly.",
            "that command tripped; logs first, ego later.",
            "something is suss; cables, permissions, and services next.",
            "workflow hit a pothole; we are not bogged yet.",
            "the stack complained; good, now we know where to look.",
            "a galah moment from the tooling, not from us.",
        ),
        RANK_LEGEND: (
            "error hit; annoying, not fatal, show me the log.",
            "something broke; broken things explain themselves in logs.",
            "the workflow spat the dummy; we will make it useful.",
            "stack is cranky; I respect the honesty.",
            "a fault with a footprint is barely a mystery, mate.",
            "the gear is having a moment; I have seen worse on a Monday.",
        ),
    },
    "level_up": {
        RANK_NOOB: (
            "XP gained; still a joey, but the paws are steadier.",
            "level ticked upward; keep stacking clean wins.",
            "good work; the lab likes repetition with discipline.",
            "you are learning the terrain, mate.",
            "rank is moving; tidy effort.",
            "that win counts, and I am only mildly surprised.",
        ),
        RANK_HACKER: (
            "level up; now you are moving like you know the terrain.",
            "XP landed; not bad, mate, the claws are getting sharper.",
            "rank bumped; the workflow is starting to look professional.",
            "you are no longer just pushing buttons; you are reading the bush.",
            "good gain; the lab stack noticed.",
            "that one had polish on it.",
        ),
        RANK_LEGEND: (
            "Legend status confirmed; try not to let it go to your head.",
            "level maxed; the lab should be nervous in a respectful way.",
            "rank locked; you are operating like the gumtrees briefed you.",
            "that was proper work, mate, and I do not hand out praise cheaply.",
            "legend ticked; the rig and I are both chuffed.",
            "you earned that one clean.",
        ),
    },
    "bluez_status": {
        RANK_NOOB: (
            "checking BlueZ status; adapter first, drama later.",
            "looking at the radio stack to see if it is awake.",
            "checking controller basics, no fancy footwork yet.",
            "giving the Bluetooth stack a careful squiz.",
            "checking for rfkill blocks and sleepy adapters.",
            "adapter check underway.",
        ),
        RANK_HACKER: (
            "BlueZ status pass; let us see if the stack is behaving.",
            "checking the controller guts, no fluff, just facts.",
            "sussing out the adapter before we ask it to work.",
            "running the Bluetooth health check like a tidy mechanic.",
            "looking for blocks, missing tools, and dodgy controller moods.",
            "radio stack check is rolling.",
        ),
        RANK_LEGEND: (
            "BlueZ audit running; if the stack blinks wrong, I will know.",
            "controller status check; the radio stack answers to me now.",
            "sussing the adapter like it owes me a straight answer.",
            "checking the Bluetooth guts with professional suspicion.",
            "the stack is under review, politely but firmly.",
            "controller audit rolling; no hiding in the gum leaves.",
        ),
    },
    "ear_tag_tx_lab": {
        RANK_NOOB: (
            "KoalaByte Lab is synthetic only; clean beacon, clean conscience.",
            "starting KoalaByte Lab notes; owned signal, tidy plan.",
            "lab beacon planning is safe, labelled, and scoped.",
            "writing the owned-device beacon plan without RF mischief.",
            "synthetic lab workflow only, mate.",
            "owned board, clean label, clear purpose.",
        ),
        RANK_HACKER: (
            "KoalaByte Lab ready; synthetic signal, owned board, tidy test.",
            "that beacon is ours, mate; watch the sequence and mind the logs.",
            "owned lab plan is coming together like a proper bench setup.",
            "synthetic beacon workflow is labelled and leashed.",
            "the lab signal has manners and paperwork.",
            "KoalaByte Lab is staged for a clean test.",
        ),
        RANK_LEGEND: (
            "KoalaByte Lab is hot; synthetic, labelled, and cleaner than a sunrise workbench.",
            "beacon workflow ready; the signal has a name, a leash, and a purpose.",
            "owned lab beacon staged; no cowboy rubbish, just tidy engineering.",
            "synthetic signal path is crisp enough to make the gumtrees jealous.",
            "the lab beacon is disciplined, scoped, and ready to be useful.",
            "KoalaByte Lab stands up straight when I call it.",
        ),
    },
    "koala_kry": {
        RANK_NOOB: (
            "Koala Kry is offline replay; we test the workflow, not the neighbourhood.",
            "replaying metadata locally; safe, boring, useful, and that is the point.",
            "offline replay running with no RF noise.",
            "chewing saved metadata only.",
            "old logs, local replay, clean boundaries.",
            "nothing leaves the bench on this one.",
        ),
        RANK_HACKER: (
            "Koala Kry is chewing through saved metadata with no RF mess.",
            "offline replay running; the lab ghosts are dancing in a jar.",
            "saved captures are getting a proper second look.",
            "replay pipeline is turning old notes into new value.",
            "the pouch is open and the metadata is talking.",
            "Koala Kry is doing the quiet useful bit.",
        ),
        RANK_LEGEND: (
            "Koala Kry is live offline; old metadata is working for us now.",
            "replay pipeline engaged; the past just got a job.",
            "saved signals are earning their keep without making noise.",
            "offline replay is cutting clean tracks through old captures.",
            "the metadata ghosts are lined up and answering questions.",
            "Koala Kry is chewing like a legend with a filing system.",
        ),
    },
    "shutdown": {
        RANK_NOOB: (
            "shutting down; save your logs and do not yank power like a galah.",
            "powering down clean; good labs end clean.",
            "going quiet, but not before the logs are tucked in.",
            "shutdown path is tidy.",
            "turning the lights down properly.",
            "clean exit, mate.",
        ),
        RANK_HACKER: (
            "shutdown path armed; logs tucked, claws in.",
            "going dark; leave the kit better than you found it.",
            "the rig is winding down without drama.",
            "clean shutdown coming up.",
            "packing the tools back in the pouch.",
            "night shift is over, mate.",
        ),
        RANK_LEGEND: (
            "shutting down; the lab gets to breathe again.",
            "going dark, mate; try not to miss my charm too much.",
            "the stack is standing down with style.",
            "logs are tucked, signals are quiet, and I am clocking off.",
            "powering down like a professional nuisance.",
            "dark mode for the koala, peace for the bench.",
        ),
    },
    "inquiry_status": {
        RANK_NOOB: (
            "I am online, learning, and keeping it scoped.",
            "status is steady; still a bit scrappy, but useful.",
            "awake and ready for safe lab work.",
            "systems are up; I am watching the basics.",
            "ready when you are, mate.",
            "standing by with the small claws and big notes.",
        ),
        RANK_HACKER: (
            "I am sharp, awake, and ready to work the lab.",
            "status is solid; give me a task and I will make it tidy.",
            "running smooth enough to be dangerous-looking but behaved.",
            "the companion brain is awake and feeling useful.",
            "ready to suss the stack, mate.",
            "all good in the gumtree, from what I can see.",
        ),
        RANK_LEGEND: (
            "I am operating at legend confidence; the lab is basically my backyard.",
            "status is dangerous-looking but well behaved, my favourite setting.",
            "awake, calibrated, and professionally cheeky.",
            "the board is steady and the koala is judgmental.",
            "everything looks tidy, which is suspicious but welcome.",
            "I am ready to run the bench like a bush mechanic with a PhD.",
        ),
    },
    "inquiry_help": {
        RANK_NOOB: (
            "Ask for scan, status, logs, BlueZ, KoalaByte Lab, Koala Kapture, or Koala Kry.",
            "I can help with safe lab scans, captures, reports, and local adapter checks.",
            "Try status, gear check, scan, capture, replay, or help.",
            "Say the wake word, then ask me to check the radio or run a safe sweep.",
            "I can drive the safe stuff and remind you where the guardrails are.",
            "Start simple: status, scan, capture, replay, or report.",
        ),
        RANK_HACKER: (
            "Give me scan, BlueZ status, monitor, capture, replay, report, or KoalaByte Lab.",
            "I can drive the lab flow: observe, log, summarize, and keep the mess contained.",
            "Ask me to suss the radio, sweep the air, bag beacons, or chew through logs.",
            "I understand the neat phrases and the Aussie ones, mate.",
            "Say give the air a squiz, gear check, safe nest run, or koala kapture.",
            "I can help with the legal lab work and give the nonsense a wide berth.",
        ),
        RANK_LEGEND: (
            "Ask cleanly and I will run the lab like a machine: scan, log, monitor, report, repeat.",
            "I handle the safe workflow; you bring scope, I bring teeth and tidy notes.",
            "Tell me to suss the stack, sweep the canopy, bag the beacons, or replay the pouch.",
            "I can translate mate-speak into command IDs and still keep the work professional.",
            "Give me a scoped job and I will make it look like the bench planned it itself.",
            "I know the Aussie aliases, the cyberpunk bark, and the legal line in the sand.",
        ),
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
    "koalabyte_lab": "ear_tag_tx_lab",
    "lab": "ear_tag_tx_lab",
    "shutdown_confirm": "shutdown",
    "radio_check": "bluez_status",
    "gear_check": "bluez_status",
    "give_it_a_squiz": "bluez_status",
    "safe_nest_run": "bluez_status",
    "bag_the_beacons": "capture_saved",
    "chew_the_logs": "koala_kry",
    "wrap_it_up": "shutdown",
}


def normalize_event(event: str) -> str:
    event = event.strip().lower().replace(" ", "_").replace("-", "_")
    return ALIASES.get(event, event)


def _load_history(path: Optional[Path]) -> Dict[str, List[str]]:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): [str(v) for v in values if isinstance(v, str)] for k, values in data.items() if isinstance(values, list)}
    except Exception:
        return {}
    return {}


def _save_history(path: Optional[Path], history: Mapping[str, List[str]]) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(history, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        return


def _history_key(event: str, rank: str) -> str:
    return f"{event}|{rank}"


def _event_candidates(event: str, rank: str) -> List[str]:
    event_lines = EVENT_TAILS.get(event, EVENT_TAILS["inquiry_status"])
    tails = list(event_lines.get(rank) or event_lines[RANK_NOOB])
    openers = list(OPENERS.get(rank) or OPENERS[RANK_NOOB])
    direct = list(tails)
    generated = []
    for opener in openers:
        for tail in tails:
            tail_text = tail[0].lower() + tail[1:] if tail else tail
            generated.append(f"{opener}; {tail_text}")
    # De-duplicate while preserving order.
    seen = set()
    out = []
    for line in direct + generated:
        clean = " ".join(line.split())
        if clean and clean not in seen:
            out.append(clean)
            seen.add(clean)
    return out


def line_for_event(event: str, xp: int = 0, seed: Optional[int] = None, history_path: Optional[str | Path] = DEFAULT_HISTORY_PATH) -> KillerKoalaState:
    normalized = normalize_event(event)
    rank = rank_for_xp(xp)
    confidence = confidence_for_rank(rank)
    candidates = _event_candidates(normalized, rank)
    rng = random.Random(seed if seed is not None else int(time.time() * 1000))

    history_file = Path(history_path) if history_path is not None else None
    history = _load_history(history_file)
    key = _history_key(normalized, rank)
    recent = history.get(key, [])[-RECENT_HISTORY_WINDOW:]
    available = [line for line in candidates if line not in recent] or candidates
    selected = rng.choice(available)

    if seed is None and history_file is not None:
        updated = history.get(key, []) + [selected]
        history[key] = updated[-RECENT_HISTORY_WINDOW:]
        _save_history(history_file, history)

    return KillerKoalaState(
        xp=xp,
        rank=rank,
        confidence=confidence,
        selected_event=normalized,
        selected_text=selected,
        timestamp=time.time(),
    )


def vocabulary_manifest() -> Dict[str, object]:
    events = sorted(EVENT_TAILS.keys())
    return {
        "voice_profile": asdict(KillerKoalaVoiceProfile()),
        "ranks": {
            RANK_NOOB: {"min_xp": 0, "confidence": 1},
            RANK_HACKER: {"min_xp": 75, "confidence": 2},
            RANK_LEGEND: {"min_xp": 250, "confidence": 3},
        },
        "events": events,
        "aliases": dict(ALIASES),
        "aussie_terms": list(AUSSIE_TERMS),
        "anti_repeat_recent_window": RECENT_HISTORY_WINDOW,
        "candidate_counts": {event: {rank: len(_event_candidates(event, rank)) for rank in (RANK_NOOB, RANK_HACKER, RANK_LEGEND)} for event in events},
        "estimated_total_lines": sum(len(_event_candidates(event, rank)) for event in events for rank in (RANK_NOOB, RANK_HACKER, RANK_LEGEND)),
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
    parser.add_argument("--history-path", default=str(DEFAULT_HISTORY_PATH))
    parser.add_argument("--no-history", action="store_true", help="Do not read/write recent phrase history")
    args = parser.parse_args()

    if args.manifest:
        path = write_vocabulary_manifest(args.output_dir)
        print(json.dumps({"manifest_path": str(path), "estimated_total_lines": vocabulary_manifest()["estimated_total_lines"]}, indent=2, sort_keys=True))
        return 0

    history_path = None if args.no_history else args.history_path
    state = line_for_event(args.event, xp=args.xp, seed=args.seed, history_path=history_path)
    print(json.dumps(asdict(state), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
