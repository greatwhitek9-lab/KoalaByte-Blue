from __future__ import annotations

from pathlib import Path


def patch_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} expected one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def require_once(path: Path, marker: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label} expected one marker, found {count}")


def apply(project: Path) -> None:
    config = project / "include" / "config.h"
    audio = project / "src" / "dualeye_audio.cpp"

    patch_once(
        config,
        "#define MIC_INPUT_DIGITAL_GAIN_DB 22",
        "#define MIC_INPUT_DIGITAL_GAIN_DB 0",
        "vendor microphone digital-gain patch",
    )
    # Keep the source 0.010 RMS wake gate. Bench telemetry with this vendor
    # gain profile showed a much lower idle floor than normal spoken input, so
    # the former 0.030 override prevented ordinary speech from opening capture.
    require_once(
        config,
        "#define MIC_WAKE_RMS_THRESHOLD 0.010f",
        "calibrated microphone energy-gate",
    )
    patch_once(
        audio,
        "inputConfig.mic_gain = ES7210_MIC_GAIN_37_5DB;",
        "inputConfig.mic_gain = ES7210_MIC_GAIN_30DB;",
        "vendor microphone analog-gain patch",
    )

    print(
        "Applied calibrated ES7210 profile: 30 dB analog, 0 dB digital, 0.010 RMS wake gate"
    )


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    apply(project)
elif __name__ == "__main__":
    apply(Path(__file__).resolve().parents[1])
