from __future__ import annotations

from typing import Any, Callable

from .esp32_dualeye_sphinx_bridge import (
    _command_grammar_for_root,
    _command_grammar_enabled,
    resolve_pocketsphinx_model,
)


def install_esp32_pocketsphinx_decoder_cache(bridge_cls: type[Any]) -> type[Any]:
    """Reuse PocketSphinx decoders instead of rebuilding them for every utterance.

    The physical DualEye microphone can produce frequent short captures. Building
    a Decoder reloads the acoustic model and JSGF graph, which blocks the same
    bridge loop that drains K1-K6 display commands. Reusing the decoder keeps
    recognition synchronous but removes repeated model/grammar construction.
    """

    if getattr(bridge_cls, "_koalabyte_pocketsphinx_decoder_cache_installed", False):
        return bridge_cls

    original_command: Callable[..., str] = bridge_cls._transcribe_with_command_grammar
    original_general: Callable[..., str] = bridge_cls._transcribe_with_pocketsphinx

    def _reset_decoder(instance: Any, name: str) -> None:
        setattr(instance, name, None)

    def _cached_command(self: Any, pcm: bytes, sample_rate: int, sample_width: int) -> str:
        if not pcm or sample_rate != 16000 or sample_width != 2 or not _command_grammar_enabled():
            return ""
        root = resolve_pocketsphinx_model()
        if root is None:
            return ""
        try:
            from pocketsphinx import Decoder  # type: ignore

            decoder = getattr(self, "_koalabyte_command_decoder", None)
            if decoder is None:
                grammar = _command_grammar_for_root(root)
                decoder = Decoder(
                    hmm=str(root / "en-us"),
                    jsgf=str(grammar.path),
                    dict=str(grammar.dictionary_path),
                    samprate=sample_rate,
                    loglevel="ERROR",
                )
                self._koalabyte_command_decoder = decoder

            decoder.start_utt()
            decoder.process_raw(pcm, False, True)
            decoder.end_utt()
            hypothesis = decoder.hyp()
            if hypothesis is None:
                return ""
            phrase = " ".join(str(hypothesis.hypstr or "").lower().split())
            if not (
                phrase.startswith("killer koala ")
                or phrase.startswith("hey killer koala ")
            ):
                return ""
            return phrase
        except Exception:
            _reset_decoder(self, "_koalabyte_command_decoder")
            try:
                return original_command(self, pcm, sample_rate, sample_width)
            except Exception:
                return ""

    def _cached_general(self: Any, pcm: bytes, sample_rate: int, sample_width: int) -> str:
        if not pcm or sample_rate != 16000 or sample_width != 2:
            return ""
        root = resolve_pocketsphinx_model()
        if root is None:
            return ""
        try:
            from pocketsphinx import Decoder  # type: ignore

            decoder = getattr(self, "_koalabyte_general_decoder", None)
            if decoder is None:
                decoder = Decoder(
                    hmm=str(root / "en-us"),
                    lm=str(root / "en-us.lm.bin"),
                    dict=str(root / "cmudict-en-us.dict"),
                    samprate=sample_rate,
                    loglevel="ERROR",
                )
                self._koalabyte_general_decoder = decoder

            decoder.start_utt()
            decoder.process_raw(pcm, False, True)
            decoder.end_utt()
            hypothesis = decoder.hyp()
            return str(hypothesis.hypstr or "").strip() if hypothesis is not None else ""
        except Exception:
            _reset_decoder(self, "_koalabyte_general_decoder")
            try:
                return original_general(self, pcm, sample_rate, sample_width)
            except Exception:
                return ""

    bridge_cls._transcribe_with_command_grammar = _cached_command
    bridge_cls._transcribe_with_pocketsphinx = _cached_general
    bridge_cls._koalabyte_command_decoder = None
    bridge_cls._koalabyte_general_decoder = None
    bridge_cls._koalabyte_pocketsphinx_decoder_cache_installed = True
    return bridge_cls


__all__ = ["install_esp32_pocketsphinx_decoder_cache"]
