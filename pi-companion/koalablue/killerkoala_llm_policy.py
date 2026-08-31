from __future__ import annotations

from typing import Callable


def command_fastpath_should_try_llm(event: str, flexible: bool, config) -> bool:
    """Use TinyLlama only when semantic generation is actually needed.

    Ordinary command acknowledgements use the local phrase engine so an Ollama
    timeout cannot delay execution feedback. General questions and explicitly
    flexible/banter requests retain TinyLlama.
    """

    if str(getattr(config, "mode", "")).strip().lower() in {
        "off",
        "disabled",
        "phrase",
        "phrase_only",
    }:
        return False
    return bool(flexible or str(event or "").strip() == "inquiry_question")


def install_killerkoala_llm_fastpath() -> Callable:
    """Install the production voice-service LLM routing policy."""

    from . import killerkoala_hybrid_companion as companion

    companion.should_try_llm = command_fastpath_should_try_llm
    return command_fastpath_should_try_llm


__all__ = [
    "command_fastpath_should_try_llm",
    "install_killerkoala_llm_fastpath",
]
