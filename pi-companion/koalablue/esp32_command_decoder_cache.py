from __future__ import annotations

from typing import Any, Callable


def install_esp32_command_decoder_cache(bridge_cls: type[Any]) -> type[Any]:
    """Reuse one PocketSphinx JSGF decoder across command-only utterances.

    Reconstructing the acoustic model, dictionary, and JSGF decoder for every
    ambient capture can block the single ESP32 owner loop long enough to delay
    K1-K6 display traffic. PocketSphinx decoders support repeated start/end
    utterance cycles, so keep one command decoder per bridge instance and rebuild
    it only after a decoding failure.
    """

    if getattr(bridge_cls, "_koalabyte_command_decoder_cache_installed", False):
        return bridge_cls

    original: Callable[..., str] = bridge_cls._transcribe_with_command_grammar

    def _transcribe_with_command_grammar(
        self: Any,
        pcm: bytes,
        sample_rate: int,
        sample_width: int,
    ) -> str:
        if not pcm or sample_rate != 16000 or sample_width != 2:
            return ""

        try:
            from . import esp32_dualeye_sphinx_bridge as sphinx_bridge

            if not sphinx_bridge._command_grammar_enabled():
                return ""
            root = sphinx_bridge.resolve_pocketsphinx_model()
            if root is None:
                return ""

            decoder = getattr(self, "_koalabyte_command_decoder", None)
            decoder_root = getattr(self, "_koalabyte_command_decoder_root", "")
            resolved_root = str(root.resolve())
            if decoder is None or decoder_root != resolved_root:
                from pocketsphinx import Decoder  # type: ignore

                grammar = sphinx_bridge._command_grammar_for_root(root)
                decoder = Decoder(
                    hmm=str(root / "en-us"),
                    jsgf=str(grammar.path),
                    dict=str(grammar.dictionary_path),
                    samprate=sample_rate,
                    loglevel="ERROR",
                )
                self._koalabyte_command_decoder = decoder
                self._koalabyte_command_decoder_root = resolved_root

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
            self._koalabyte_command_decoder = None
            self._koalabyte_command_decoder_root = ""
            return ""

    _transcribe_with_command_grammar._koalabyte_command_decoder_cache = True  # type: ignore[attr-defined]
    bridge_cls._transcribe_with_command_grammar = _transcribe_with_command_grammar
    bridge_cls._koalabyte_command_decoder_cache_installed = True
    bridge_cls._koalabyte_command_decoder = None
    bridge_cls._koalabyte_command_decoder_root = ""
    return bridge_cls


__all__ = ["install_esp32_command_decoder_cache"]
