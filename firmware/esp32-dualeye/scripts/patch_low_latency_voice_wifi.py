from __future__ import annotations

from pathlib import Path


OLD_SLEEP = "  WiFi.setSleep(true);\n"
NEW_SLEEP = (
    "  // Continuous 16 kHz voice PCM must not be paced by Wi-Fi power-save\n"
    "  // beacon intervals. Keep the station awake so synchronous UDP sends do\n"
    "  // not starve the I2S capture loop.\n"
    "  WiFi.setSleep(false);\n"
)


def apply_low_latency_voice_wifi(source: Path) -> None:
    text = source.read_text(encoding="utf-8")

    if NEW_SLEEP in text:
        if text.count(NEW_SLEEP) != 1:
            raise RuntimeError(
                "low-latency voice Wi-Fi patch found duplicate patched anchors"
            )
        print(
            "DualEye Wi-Fi station already patched for low-latency continuous voice PCM"
        )
        return

    count = text.count(OLD_SLEEP)
    if count != 1:
        raise RuntimeError(
            f"low-latency voice Wi-Fi patch expected one sleep anchor, found {count}"
        )

    text = text.replace(OLD_SLEEP, NEW_SLEEP, 1)

    required = (
        "Continuous 16 kHz voice PCM",
        "WiFi.setSleep(false);",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError(f"low-latency voice Wi-Fi output missing markers: {missing}")

    source.write_text(text, encoding="utf-8")
    print(
        "Patched DualEye Wi-Fi station for low-latency continuous voice PCM; "
        "power-save disabled while connected"
    )


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    apply_low_latency_voice_wifi(project / "src" / "integrated_main.cpp")
elif __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    apply_low_latency_voice_wifi(project / "src" / "integrated_main.cpp")
