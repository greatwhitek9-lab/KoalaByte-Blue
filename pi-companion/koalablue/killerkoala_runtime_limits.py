from __future__ import annotations

import os
from typing import Any


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def install_killerkoala_runtime_limits() -> None:
    """Replace the legacy fixed 2048-token request with bounded runtime settings.

    Ollama's service-level context default is not sufficient because the companion
    request historically supplied ``num_ctx=2048`` on every call. This installer
    runs when the koalablue package is imported, so menu, voice, diagnostics, and
    command-line use all share the same Pi-safe request policy.
    """

    from . import killerkoala_hybrid_companion as companion

    if getattr(companion, "_koalabyte_runtime_limits_installed", False):
        return

    def bounded_ollama_generate(config: Any, prompt: str) -> str:
        num_ctx = _bounded_int("KILLERKOALA_LLM_NUM_CTX", 768, 256, 2048)
        num_predict = _bounded_int(
            "KILLERKOALA_LLM_NUM_PREDICT",
            min(int(config.num_predict), 96),
            16,
            192,
        )
        payload = {
            "model": config.model,
            "prompt": prompt,
            "system": companion._system_prompt(),
            "stream": False,
            "keep_alive": os.getenv("KILLERKOALA_LLM_KEEP_ALIVE", "60s"),
            "options": {
                "num_predict": num_predict,
                "temperature": 0.72,
                "top_p": 0.9,
                "repeat_penalty": 1.12,
                "num_ctx": num_ctx,
            },
        }
        with companion.httpx.Client(timeout=config.timeout_seconds) as client:
            response = client.post(f"{config.host}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return str(data.get("response", ""))

    companion._ollama_generate = bounded_ollama_generate
    companion.DEFAULT_NUM_PREDICT = min(companion.DEFAULT_NUM_PREDICT, 96)
    companion.DEFAULT_MAX_RESPONSE_CHARS = min(
        companion.DEFAULT_MAX_RESPONSE_CHARS, 420
    )
    companion.DEFAULT_DIALOGUE_TURNS = min(companion.DEFAULT_DIALOGUE_TURNS, 2)
    companion._koalabyte_runtime_limits_installed = True


__all__ = ["install_killerkoala_runtime_limits"]
