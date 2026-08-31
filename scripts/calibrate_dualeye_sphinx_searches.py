#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import time
import wave
from pathlib import Path
from typing import Any

from koalablue.esp32_dualeye_sphinx_bridge import (
    _decode_binary_pcm_packet,
    resolve_pocketsphinx_model,
)

RATE = 16000
WIDTH = 2
DEFAULT_PORT = 42110
DEFAULT_THRESHOLDS = (1e-20, 1e-25, 1e-30, 1e-35, 1e-40)


def _recognize_keyphrase(pcm: bytes, root: Path, threshold: float) -> str:
    from pocketsphinx import Decoder

    decoder = Decoder(
        hmm=str(root / "en-us"),
        dict=str(root / "cmudict-en-us.dict"),
        keyphrase="killer koala",
        kws_threshold=threshold,
        samprate=RATE,
        loglevel="ERROR",
    )
    decoder.start_utt()
    decoder.process_raw(pcm, False, True)
    decoder.end_utt()
    hyp = decoder.hyp()
    return str(hyp.hypstr).strip() if hyp is not None else ""


def _recognize_general(pcm: bytes, root: Path) -> str:
    from pocketsphinx import Decoder

    decoder = Decoder(
        hmm=str(root / "en-us"),
        lm=str(root / "en-us.lm.bin"),
        dict=str(root / "cmudict-en-us.dict"),
        samprate=RATE,
        loglevel="ERROR",
    )
    decoder.start_utt()
    decoder.process_raw(pcm, False, True)
    decoder.end_utt()
    hyp = decoder.hyp()
    return str(hyp.hypstr).strip() if hyp is not None else ""


def _recognize_exact_grammar(pcm: bytes, root: Path, grammar_path: Path) -> str:
    from pocketsphinx import Decoder

    decoder = Decoder(
        hmm=str(root / "en-us"),
        dict=str(root / "cmudict-en-us.dict"),
        jsgf=str(grammar_path),
        samprate=RATE,
        loglevel="ERROR",
    )
    decoder.start_utt()
    decoder.process_raw(pcm, False, True)
    decoder.end_utt()
    hyp = decoder.hyp()
    return str(hyp.hypstr).strip() if hyp is not None else ""


def _write_wav(path: Path, pcm: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(WIDTH)
        handle.setframerate(RATE)
        handle.writeframes(pcm)


def _grammar_for_phrase(phrase: str) -> str:
    clean = " ".join(str(phrase).lower().split())
    return (
        "#JSGF V1.0;\n"
        "grammar killerkoala_calibration;\n"
        f"public <command> = {clean};\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare PocketSphinx KWS, exact JSGF, and general LM on identical DualEye KPCM audio."
    )
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--phrase", default="killer koala status")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--output-dir",
        default="logs/killerkoala/stt-calibration",
    )
    args = parser.parse_args()

    root = resolve_pocketsphinx_model()
    if root is None:
        raise SystemExit("POCKETSPHINX_MODEL_NOT_READY")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = output_dir / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    grammar_path = run_dir / "exact_command.gram"
    grammar_path.write_text(_grammar_for_phrase(args.phrase), encoding="utf-8")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", args.port))
    sock.settimeout(0.5)

    sessions: dict[str, dict[str, Any]] = {}
    pending: dict[str, list[dict[str, Any]]] = {}
    results: list[dict[str, Any]] = []
    deadline = time.time() + max(45, args.samples * 20)

    print(f'Say "{args.phrase.title()}" once each time LISTENING appears.')
    print()
    print(f"LISTENING 1/{args.samples}")

    try:
        while len(results) < args.samples and time.time() < deadline:
            try:
                data, peer = sock.recvfrom(65535)
            except socket.timeout:
                continue

            binary = _decode_binary_pcm_packet(data)
            if binary is not None:
                rid = str(binary["request_id"])
                packet = {
                    "sequence": int(binary["sequence"]),
                    "pcm": bytes(binary["_pcm_s16le_mono"]),
                    "batch_frames": int(binary["batch_frames"]),
                    "packet_bytes": len(data),
                }
                if rid in sessions:
                    sessions[rid]["packets"].append(packet)
                else:
                    pending.setdefault(rid, []).append(packet)
                continue

            try:
                payload = json.loads(data.decode("utf-8", errors="ignore"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue

            payload_type = str(payload.get("type") or "")
            rid = str(payload.get("request_id") or "")

            if payload_type == "audio_utterance_start":
                sessions[rid] = {
                    "packets": pending.pop(rid, []),
                    "start_payload": payload,
                    "peer": peer,
                }
                continue

            if payload_type != "audio_utterance_end" or rid not in sessions:
                continue

            state = sessions.pop(rid)
            packets = sorted(state["packets"], key=lambda item: item["sequence"])
            pcm = b"".join(item["pcm"] for item in packets)
            sequences = [item["sequence"] for item in packets]
            gaps = [
                [left, right]
                for left, right in zip(sequences, sequences[1:])
                if right != left + 1
            ]

            sample_index = len(results) + 1
            wav_path = run_dir / f"sample-{sample_index:02d}.wav"
            _write_wav(wav_path, pcm)

            kws = {
                f"{threshold:.0e}": _recognize_keyphrase(pcm, root, threshold)
                for threshold in DEFAULT_THRESHOLDS
            }
            grammar = _recognize_exact_grammar(pcm, root, grammar_path)
            general = _recognize_general(pcm, root)

            result = {
                "sample": sample_index,
                "request_id": rid,
                "packets": len(packets),
                "packet_sizes": sorted({item["packet_bytes"] for item in packets}),
                "batch_frames": sorted({item["batch_frames"] for item in packets}),
                "pcm_bytes": len(pcm),
                "audio_seconds": round(len(pcm) / (RATE * WIDTH), 3),
                "sequence_gaps": gaps,
                "kws": kws,
                "exact_jsgf": grammar,
                "general_lm": general,
                "wav": str(wav_path),
            }
            results.append(result)

            print()
            print(f"=== SAMPLE {sample_index}/{args.samples} ===")
            print("packets      =", result["packets"])
            print("pcm_bytes    =", result["pcm_bytes"])
            print("audio_sec    =", result["audio_seconds"])
            print("sequence_gap =", gaps if gaps else "NONE")
            for threshold, hypothesis in kws.items():
                print(f"kws {threshold:>5}   =", repr(hypothesis or "NOT DETECTED"))
            print("exact_jsgf   =", repr(grammar or "NOT DETECTED"))
            print("general_lm   =", repr(general))
            print("wav          =", wav_path)

            if len(results) < args.samples:
                print()
                print(f"LISTENING {len(results) + 1}/{args.samples}")
    finally:
        sock.close()

    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "phrase": args.phrase,
                "model_root": str(root),
                "thresholds": DEFAULT_THRESHOLDS,
                "samples_requested": args.samples,
                "samples_completed": len(results),
                "results": results,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print()
    print("=== SUMMARY ===")
    print("samples =", len(results))
    for threshold in DEFAULT_THRESHOLDS:
        key = f"{threshold:.0e}"
        detected = sum(1 for item in results if item["kws"].get(key) == "killer koala")
        print(f"kws {key:>5} = {detected}/{len(results)}")
    grammar_hits = sum(1 for item in results if item["exact_jsgf"])
    print(f"exact_jsgf = {grammar_hits}/{len(results)}")
    print("summary =", summary_path)

    return 0 if len(results) == args.samples else 2


if __name__ == "__main__":
    raise SystemExit(main())
