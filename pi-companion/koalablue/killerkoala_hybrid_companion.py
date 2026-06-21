from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import httpx

from .killerkoala_vocabulary import line_for_event, rank_for_xp

DEFAULT_TRACE_DIR = Path("logs/killerkoala")
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "killerkoala-tinyllama:latest"
DEFAULT_TIMEOUT_SECONDS = 2.5
DEFAULT_NUM_PREDICT = 72
DEFAULT_MAX_RESPONSE_CHARS = 260


@dataclass(frozen=True)
class KillerKoalaLLMConfig:
    mode: str
    model: str
    host: str
    timeout_seconds: float
    num_predict: int
    max_response_chars: int
    lora_expected: bool
    lora_training_doc: str
    modelfile_path: str


@dataclass
class KillerKoalaCompanionResponse:
    event: str
    xp: int
    rank: str
    text: str
    source: str
    phrase_engine_text: str
    llm_model: str
    llm_used: bool
    llm_requested: bool
    fallback_reason: str
    generated_at: float


def load_config() -> KillerKoalaLLMConfig:
    return KillerKoalaLLMConfig(
        mode=os.getenv("KILLERKOALA_LLM_MODE", "fast_default").strip().lower(),
        model=os.getenv("KILLERKOALA_LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        host=os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).strip().rstrip("/") or DEFAULT_OLLAMA_HOST,
        timeout_seconds=float(os.getenv("KILLERKOALA_LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
        num_predict=int(os.getenv("KILLERKOALA_LLM_NUM_PREDICT", str(DEFAULT_NUM_PREDICT))),
        max_response_chars=int(os.getenv("KILLERKOALA_LLM_MAX_CHARS", str(DEFAULT_MAX_RESPONSE_CHARS))),
        lora_expected=os.getenv("KILLERKOALA_LLM_LORA_EXPECTED", "1").strip() not in {"0", "false", "False", "no"},
        lora_training_doc="docs/KILLERKOALA_LORA_TRAINING.md",
        modelfile_path="training/killerkoala_lora/Modelfile.killerkoala-tinyllama",
    )


def _safe_context_summary(context: Optional[Mapping[str, Any]]) -> str:
    if not context:
        return ""
    allowed: Dict[str, Any] = {}
    for key in ("module", "module_title", "status", "rank_before", "rank_after", "xp_reward", "error"):
        if key in context:
            allowed[key] = context[key]
    text = json.dumps(allowed, sort_keys=True) if allowed else ""
    return text[:500]


def _system_prompt() -> str:
    return (
        "You are KillerKoala, the KoalaByte Blue AI cyberpet companion. "
        "Voice: gruff, cheeky, cyberpunk, Australian slang and colloquialism, but useful. "
        "Scope: authorized lab diagnostics, defensive or educational Bluetooth workflows, status narration, reports, and companion banter. "
        "Keep replies short, varied, natural, and safety-minded. Do not mention that you are an LLM."
    )


def _build_prompt(event: str, xp: int, rank: str, phrase_engine_text: str, user_text: str = "", context: Optional[Mapping[str, Any]] = None) -> str:
    context_summary = _safe_context_summary(context)
    return f"""Rewrite or extend the fallback companion line into one fresh KillerKoala response.

Event: {event}
XP: {xp}
Rank: {rank}
User phrase: {user_text[:180]}
Safe context: {context_summary}
Fallback line: {phrase_engine_text}

Requirements:
- one response only
- under 40 words
- Australian slang or colloquial flavor
- gruff cyberpunk attitude
- safe lab-oriented wording
- no Markdown list
"""


def _clean_llm_text(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    cleaned = cleaned.strip(' "')
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned


def _ollama_generate(config: KillerKoalaLLMConfig, prompt: str) -> str:
    payload = {
        "model": config.model,
        "prompt": prompt,
        "system": _system_prompt(),
        "stream": False,
        "options": {
            "num_predict": config.num_predict,
            "temperature": 0.85,
            "top_p": 0.9,
            "num_ctx": 1024,
        },
    }
    with httpx.Client(timeout=config.timeout_seconds) as client:
        response = client.post(f"{config.host}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    return str(data.get("response", ""))


def should_try_llm(event: str, flexible: bool, config: KillerKoalaLLMConfig) -> bool:
    if config.mode in {"off", "disabled", "phrase", "phrase_only"}:
        return False
    if config.mode in {"force", "force_llm", "llm"}:
        return True
    return bool(flexible or event == "banter")


def companion_response(
    event: str,
    xp: int = 0,
    user_text: str = "",
    context: Optional[Mapping[str, Any]] = None,
    flexible: bool = False,
    history_path: Optional[str | Path] = None,
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
) -> KillerKoalaCompanionResponse:
    config = load_config()
    history_target = history_path if history_path is not None else None
    fallback_state = line_for_event(event, xp=xp, history_path=history_target)
    phrase_text = fallback_state.selected_text
    rank = rank_for_xp(xp)
    llm_requested = should_try_llm(fallback_state.selected_event, flexible, config)

    source = "phrase_engine"
    text = phrase_text
    fallback_reason = ""
    llm_used = False

    if llm_requested:
        try:
            prompt = _build_prompt(fallback_state.selected_event, xp, rank, phrase_text, user_text=user_text, context=context)
            candidate = _clean_llm_text(_ollama_generate(config, prompt), config.max_response_chars)
            if candidate:
                text = candidate
                source = "ollama_lora_optional"
                llm_used = True
            else:
                fallback_reason = "ollama returned empty response"
                source = "phrase_engine_fallback"
        except Exception as exc:
            fallback_reason = str(exc)
            source = "phrase_engine_fallback"

    response = KillerKoalaCompanionResponse(
        event=fallback_state.selected_event,
        xp=xp,
        rank=rank,
        text=text,
        source=source,
        phrase_engine_text=phrase_text,
        llm_model=config.model,
        llm_used=llm_used,
        llm_requested=llm_requested,
        fallback_reason=fallback_reason,
        generated_at=time.time(),
    )

    try:
        root = Path(trace_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "killerkoala_last_companion_response.json").write_text(json.dumps(asdict(response), indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass
    return response


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="KillerKoala hybrid phrase-first companion preview")
    parser.add_argument("event", nargs="?", default="status")
    parser.add_argument("--xp", type=int, default=0)
    parser.add_argument("--text", default="", help="Optional user phrase/context")
    parser.add_argument("--flexible", action="store_true", help="Allow optional tiny LLM/Ollama banter path")
    parser.add_argument("--history-path", default=str(DEFAULT_TRACE_DIR / "killerkoala_phrase_history.json"))
    parser.add_argument("--no-history", action="store_true")
    args = parser.parse_args()

    result = companion_response(
        args.event,
        xp=args.xp,
        user_text=args.text,
        flexible=args.flexible,
        history_path=None if args.no_history else args.history_path,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
