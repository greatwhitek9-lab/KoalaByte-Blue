from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import httpx

from .dualeye_tts import sanitize_spoken_identity
from .killerkoala_vocabulary import line_for_event, rank_for_xp

DEFAULT_TRACE_DIR = Path("logs/killerkoala")
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "killerkoala-tinyllama:latest"
DEFAULT_TIMEOUT_SECONDS = 45.0
DEFAULT_NUM_PREDICT = 96
DEFAULT_MAX_RESPONSE_CHARS = 420


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
    web_searched: bool
    web_available: bool
    web_provider: str
    web_sources: list[dict[str, str]]
    web_error: str
    web_research_artifact: str
    generated_at: float


def load_config() -> KillerKoalaLLMConfig:
    return KillerKoalaLLMConfig(
        mode=os.getenv("KILLERKOALA_LLM_MODE", "tinyllama").strip().lower(),
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
        "You are KillerKoala, the KoalaByte Blue local AI cyberpet companion running on a Raspberry Pi. "
        "Your identity and spoken name are always KillerKoala. "
        "William is only the hidden Australian text-to-speech voice backend; never call yourself William. "
        "Voice: gruff, cheeky, cyberpunk, Australian slang and colloquialism, but useful. "
        "For factual questions, use supplied research evidence, distinguish verified facts from uncertainty, "
        "and never invent current information. Do not claim to have searched unless research evidence is supplied. "
        "Keep replies concise, natural, safety-minded, and suitable for speech. Do not mention that you are an LLM."
    )


def _build_prompt(
    event: str,
    xp: int,
    rank: str,
    phrase_engine_text: str,
    user_text: str = "",
    context: Optional[Mapping[str, Any]] = None,
    web_context: str = "",
) -> str:
    context_summary = _safe_context_summary(context)
    if event == "inquiry_question":
        evidence = web_context or "No web evidence was available. Answer only from stable local knowledge and state when current facts cannot be verified."
        return f"""Answer the user's question as KillerKoala.

User question: {user_text[:500]}
Research evidence:
{evidence[:6000]}

Requirements:
- answer the question directly
- use the research evidence when present
- do not fabricate names, dates, prices, scores, office holders, versions, or current events
- if evidence is missing or conflicting, say what cannot be verified
- do not read URLs aloud
- one spoken response, normally under 70 words
- Australian flavor without obscuring the answer
- identify only as KillerKoala; never say your name is William
- no Markdown list
"""
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
- identify only as KillerKoala; never say your name is William
- no Markdown list
"""


def _clean_llm_text(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    cleaned = sanitize_spoken_identity(cleaned).strip(' "')
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
            "temperature": 0.55,
            "top_p": 0.9,
            "num_ctx": 2048,
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
    return True


def _fallback_line(event: str, xp: int, history_path: Optional[str | Path]) -> tuple[str, str]:
    if event == "inquiry_question":
        return (
            "TinyLlama is offline and I can't verify that one right now, mate. Check the Pi network and local AI service, then ask again.",
            event,
        )
    fallback_state = line_for_event(event, xp=xp, history_path=history_path)
    return sanitize_spoken_identity(fallback_state.selected_text), fallback_state.selected_event


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
    phrase_text, selected_event = _fallback_line(event, xp, history_path)
    rank = rank_for_xp(xp)
    llm_requested = should_try_llm(selected_event, flexible, config)

    source = "phrase_engine"
    text = phrase_text
    fallback_reason = ""
    llm_used = False
    web_searched = False
    web_available = False
    web_provider = "none"
    web_sources: list[dict[str, str]] = []
    web_error = ""
    web_research_artifact = ""
    web_context = ""

    if selected_event == "inquiry_question":
        try:
            from .killerkoala_web_research import research_question

            research = research_question(user_text)
            web_searched = research.searched
            web_available = research.internet_available
            web_provider = research.provider
            web_sources = [asdict(item) for item in research.sources]
            web_error = research.error
            web_research_artifact = research.artifact_path
            web_context = research.context
        except Exception as exc:
            web_error = str(exc)

    if llm_requested:
        try:
            prompt = _build_prompt(
                selected_event,
                xp,
                rank,
                phrase_text,
                user_text=user_text,
                context=context,
                web_context=web_context,
            )
            candidate = _clean_llm_text(_ollama_generate(config, prompt), config.max_response_chars)
            if candidate:
                text = candidate
                if selected_event == "inquiry_question" and web_sources:
                    source = "tinyllama_web_grounded"
                elif selected_event == "inquiry_question" and web_searched and not web_available:
                    source = "tinyllama_offline"
                else:
                    source = "tinyllama_local"
                llm_used = True
            else:
                fallback_reason = "TinyLlama returned an empty response"
                source = "phrase_engine_fallback"
        except Exception as exc:
            fallback_reason = str(exc)
            source = "phrase_engine_fallback"

    text = sanitize_spoken_identity(text)
    response = KillerKoalaCompanionResponse(
        event=selected_event,
        xp=xp,
        rank=rank,
        text=text,
        source=source,
        phrase_engine_text=phrase_text,
        llm_model=config.model,
        llm_used=llm_used,
        llm_requested=llm_requested,
        fallback_reason=fallback_reason,
        web_searched=web_searched,
        web_available=web_available,
        web_provider=web_provider,
        web_sources=web_sources,
        web_error=web_error,
        web_research_artifact=web_research_artifact,
        generated_at=time.time(),
    )

    try:
        root = Path(trace_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "killerkoala_last_companion_response.json").write_text(
            json.dumps(asdict(response), indent=2, sort_keys=True), encoding="utf-8"
        )
    except Exception:
        pass
    return response


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="KillerKoala TinyLlama-first local companion preview")
    parser.add_argument("event", nargs="?", default="status")
    parser.add_argument("--xp", type=int, default=0)
    parser.add_argument("--text", default="", help="Optional user phrase or question")
    parser.add_argument("--flexible", action="store_true", help="Request open-ended local TinyLlama output")
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
