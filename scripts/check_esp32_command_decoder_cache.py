#!/usr/bin/env python3
from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

from koalablue.esp32_command_decoder_cache import install_esp32_command_decoder_cache
from koalablue import esp32_dualeye_sphinx_bridge as sphinx_bridge


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    init_count = 0

    class FakeHypothesis:
        hypstr = "killer koala menu"

    class FakeDecoder:
        def __init__(self, **_kwargs):
            nonlocal init_count
            init_count += 1

        def start_utt(self):
            return None

        def process_raw(self, _pcm, _no_search, _full_utt):
            return None

        def end_utt(self):
            return None

        def hyp(self):
            return FakeHypothesis()

    fake_pocketsphinx = types.ModuleType("pocketsphinx")
    fake_pocketsphinx.Decoder = FakeDecoder
    previous_pocketsphinx = sys.modules.get("pocketsphinx")
    sys.modules["pocketsphinx"] = fake_pocketsphinx

    previous_enabled = sphinx_bridge._command_grammar_enabled
    previous_resolve = sphinx_bridge.resolve_pocketsphinx_model
    previous_grammar = sphinx_bridge._command_grammar_for_root
    sphinx_bridge._command_grammar_enabled = lambda: True
    sphinx_bridge.resolve_pocketsphinx_model = lambda: Path("/tmp/fake-sphinx")
    sphinx_bridge._command_grammar_for_root = lambda _root: SimpleNamespace(
        path=Path("/tmp/fake.gram"),
        dictionary_path=Path("/tmp/fake.dict"),
    )

    class DummyBridge:
        def _transcribe_with_command_grammar(self, *_args):
            return "legacy"

    try:
        install_esp32_command_decoder_cache(DummyBridge)
        bridge = DummyBridge()
        first = bridge._transcribe_with_command_grammar(b"\0\0" * 1600, 16000, 2)
        second = bridge._transcribe_with_command_grammar(b"\0\0" * 1600, 16000, 2)
        require(first == "killer koala menu", f"unexpected first transcript: {first!r}")
        require(second == "killer koala menu", f"unexpected second transcript: {second!r}")
        require(init_count == 1, f"decoder was constructed {init_count} times")
    finally:
        sphinx_bridge._command_grammar_enabled = previous_enabled
        sphinx_bridge.resolve_pocketsphinx_model = previous_resolve
        sphinx_bridge._command_grammar_for_root = previous_grammar
        if previous_pocketsphinx is None:
            sys.modules.pop("pocketsphinx", None)
        else:
            sys.modules["pocketsphinx"] = previous_pocketsphinx

    print("ESP32 command decoder cache check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
