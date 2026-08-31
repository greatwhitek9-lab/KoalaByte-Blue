from __future__ import annotations

from pathlib import Path


def quarantine_legacy_transport(source: Path) -> None:
    text = source.read_text(encoding="utf-8")

    old = """  ESP_SR.onEvent(onSrEvent);\n  srReady = ESP_SR.begin(dualEyeAudioBus(), kAllSpeechCommands,\n                         kAllSpeechCommandCount, SR_CHANNELS_STEREO,\n                         SR_MODE_COMMAND, srInputFormat);\n"""
    new = """  // ESP-SR is quarantined for this hardware path. The active microphone\n  // transport uses vendor-compatible ES7210 TDM RX and Pi-side wake/STT, so the\n  // obsolete Arduino I2SClass recognizer transport must not compile in.\n  srReady = false;\n"""

    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"legacy ESP-SR transport quarantine expected one begin anchor, found {count}"
        )

    text = text.replace(old, new, 1)

    if "dualEyeAudioBus()" in text:
        raise RuntimeError("legacy dualEyeAudioBus dependency remains after quarantine")
    if "ESP_SR.begin(" in text:
        raise RuntimeError("ESP_SR.begin dependency remains after quarantine")
    if "servicePiWakeSttFallback();" not in text:
        raise RuntimeError("Pi wake/STT fallback is missing after ESP-SR quarantine")

    source.write_text(text, encoding="utf-8")
    print(
        "Quarantined legacy ESP-SR I2SClass transport; vendor TDM RX + Pi wake/STT remains active"
    )


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    quarantine_legacy_transport(project / "src" / "integrated_main_wake_session.cpp")
elif __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    quarantine_legacy_transport(project / "src" / "integrated_main_wake_session.cpp")
