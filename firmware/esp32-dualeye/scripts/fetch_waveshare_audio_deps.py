Import("env")

from pathlib import Path
import hashlib
import shutil
import tempfile
import time
import urllib.request

project = Path(env.subst("$PROJECT_DIR"))
lib_root = project / "lib"
commit = "f16371ca7b7d4e17de6d6f6ea293981b37c0ca51"
marker = lib_root / ".waveshare-audio-f16371c"
base_raw = (
    "https://raw.githubusercontent.com/"
    "waveshareteam/ESP32-S3-DualEye-Touch-LCD-1.28/"
    f"{commit}/example/ESP32-S3-DualEye-LCD-1.28/Arduino-3.2.0/libraries"
)
max_driver_file_bytes = 1024 * 1024

# Git blob object IDs from the pinned Waveshare commit.  Verifying the raw
# payloads against these IDs gives us commit-pinned integrity without pulling
# the entire (now >64 MiB) upstream repository archive just for six files.
pinned_files = {
    "es8311": {
        "es8311.cpp": "7331d50d4513dd32115272032247b01f2eea060c",
        "es8311.h": "f66684377b3dad9fdfd2e71f81ff82a8090b73aa",
        "es8311_reg.h": "aeae4c0cd80a3a85a300f7d918de196aea58480f",
    },
    "es7210": {
        "es7210.cpp": "537c2579896bbd1e53f5d8cfcfef6e8856329535",
        "es7210.h": "2ddaa411c537cd46aba3e6eee5df7e275c871af7",
        "es7210_reg.h": "5d7c2ebade2a2c9373ad26bf80d238984d9d20b7",
    },
}

framework = Path(env.PioPlatform().get_package_dir("framework-arduinoespressif32"))
network_source = framework / "libraries" / "Network" / "src"
if network_source.exists():
    env.Append(CPPPATH=[str(network_source)])
    # pioarduino 55.x discovers Arduino 3 Network headers for WiFi but omits the
    # Network source archive from the final link. Publish the mirrored tree
    # atomically so an interrupted copy cannot poison the next build.
    network_parent = lib_root / "arduino_network_runtime"
    staged_network = lib_root / ".arduino_network_runtime.staging"
    if staged_network.exists():
        shutil.rmtree(staged_network)
    shutil.copytree(network_source, staged_network / "src")
    if network_parent.exists():
        shutil.rmtree(network_parent)
    staged_network.replace(network_parent)

# ESP_SR includes ESP_I2S.h from another framework library. PlatformIO's deep
# dependency scanner finds ESP_SR but does not reliably propagate that sibling
# framework-library include directory while compiling ESP_SR itself.
esp_i2s_source = framework / "libraries" / "ESP_I2S" / "src"
if esp_i2s_source.exists():
    env.Append(CPPPATH=[str(esp_i2s_source)])
else:
    raise RuntimeError(f"Arduino ESP_I2S headers not found: {esp_i2s_source}")


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def download_pinned_file(url: str, output: Path, expected_blob_sha: str) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "KoalaByte-Blue-firmware-builder/2"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                declared = response.headers.get("Content-Length")
                if declared and int(declared) > max_driver_file_bytes:
                    raise RuntimeError(
                        f"Waveshare driver file Content-Length exceeds "
                        f"{max_driver_file_bytes} bytes"
                    )
                data = response.read(max_driver_file_bytes + 1)
            if not data:
                raise RuntimeError("Waveshare driver download was empty")
            if len(data) > max_driver_file_bytes:
                raise RuntimeError(
                    f"Waveshare driver file exceeded {max_driver_file_bytes} bytes"
                )
            actual_blob_sha = git_blob_sha(data)
            if actual_blob_sha != expected_blob_sha:
                raise RuntimeError(
                    "Waveshare driver Git blob mismatch: "
                    f"expected {expected_blob_sha}, got {actual_blob_sha}"
                )
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
            return
        except Exception as exc:
            last_error = exc
            output.unlink(missing_ok=True)
            if attempt < 3:
                print(
                    f"Waveshare file download attempt {attempt}/3 failed: "
                    f"{exc}; retrying"
                )
                time.sleep(attempt * 5)
    raise RuntimeError(
        f"Waveshare driver file download failed after 3 attempts: {last_error}"
    )


if not marker.exists():
    print("Fetching six pinned Waveshare ES8311/ES7210 driver files")
    with tempfile.TemporaryDirectory(prefix="dualeye-audio-") as temp:
        staging = Path(temp) / "libraries"
        for library, files in pinned_files.items():
            for filename, expected_blob_sha in files.items():
                url = f"{base_raw}/{library}/{filename}"
                output = staging / library / filename
                download_pinned_file(url, output, expected_blob_sha)

        for library, files in pinned_files.items():
            destination = staging / library
            source_files = [
                path
                for path in destination.rglob("*")
                if path.is_file()
                and path.suffix.lower() in {".c", ".cc", ".cpp", ".h", ".hpp"}
            ]
            if len(source_files) != len(files):
                raise RuntimeError(
                    f"Pinned Waveshare library {library} expected {len(files)} "
                    f"source/header files, found {len(source_files)}"
                )

        lib_root.mkdir(parents=True, exist_ok=True)
        for library in pinned_files:
            destination = lib_root / library
            staged = staging / library
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(staged, destination)
        marker.write_text(commit + "\n", encoding="utf-8")
