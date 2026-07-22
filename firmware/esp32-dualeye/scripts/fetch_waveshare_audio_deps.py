Import("env")

from pathlib import Path
import shutil
import tempfile
import time
import urllib.request
import zipfile

project = Path(env.subst("$PROJECT_DIR"))
lib_root = project / "lib"
commit = "f16371ca7b7d4e17de6d6f6ea293981b37c0ca51"
marker = lib_root / ".waveshare-audio-f16371c"
archive = f"https://github.com/waveshareteam/ESP32-S3-DualEye-Touch-LCD-1.28/archive/{commit}.zip"
root = f"ESP32-S3-DualEye-Touch-LCD-1.28-{commit}/example/ESP32-S3-DualEye-LCD-1.28/Arduino-3.2.0/libraries"
max_archive_bytes = 64 * 1024 * 1024

framework = Path(env.PioPlatform().get_package_dir("framework-arduinoespressif32"))
network_source = framework / "libraries" / "Network" / "src"
if network_source.exists():
    env.Append(CPPPATH=[str(network_source)])
    # pioarduino 55.x discovers Arduino 3 Network headers for WiFi but omits the
    # Network source archive from the final link. Publish the mirrored tree
    # atomically so an interrupted copy cannot poison the next build.
    network_parent = lib_root / "arduino_network_runtime"
    network_library = network_parent / "src"
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


def download_with_retry(url: str, output: Path) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "KoalaByte-Blue-firmware-builder/1"},
            )
            with urllib.request.urlopen(request, timeout=60) as response, output.open("wb") as handle:
                declared = response.headers.get("Content-Length")
                if declared and int(declared) > max_archive_bytes:
                    raise RuntimeError(
                        f"Waveshare archive Content-Length exceeds {max_archive_bytes} bytes"
                    )
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_archive_bytes:
                        raise RuntimeError(
                            f"Waveshare archive exceeded {max_archive_bytes} bytes"
                        )
                    handle.write(chunk)
            if output.stat().st_size == 0:
                raise RuntimeError("Waveshare archive download was empty")
            return
        except Exception as exc:
            last_error = exc
            output.unlink(missing_ok=True)
            if attempt < 3:
                print(f"Waveshare download attempt {attempt}/3 failed: {exc}; retrying")
                time.sleep(attempt * 5)
    raise RuntimeError(f"Waveshare driver download failed after 3 attempts: {last_error}")


if not marker.exists():
    print("Fetching pinned Waveshare ES8311/ES7210 drivers")
    with tempfile.TemporaryDirectory(prefix="dualeye-audio-") as temp:
        temp_root = Path(temp)
        zip_path = temp_root / "waveshare.zip"
        staging = temp_root / "libraries"
        download_with_retry(archive, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            corrupt_member = zf.testzip()
            if corrupt_member is not None:
                raise RuntimeError(f"Waveshare ZIP CRC failed at {corrupt_member}")
            for library in ("es8311", "es7210"):
                prefix = f"{root}/{library}/"
                names = [
                    name
                    for name in zf.namelist()
                    if name.startswith(prefix) and not name.endswith("/")
                ]
                if not names:
                    raise RuntimeError(f"Missing Waveshare library {library}")
                destination = staging / library
                for name in names:
                    relative = Path(name[len(prefix) :])
                    if not relative.parts or ".." in relative.parts:
                        raise RuntimeError(f"Unsafe Waveshare ZIP path: {name}")
                    output = destination / relative
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, output.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                source_files = [
                    path
                    for path in destination.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".c", ".cc", ".cpp", ".h", ".hpp"}
                ]
                if not source_files:
                    raise RuntimeError(
                        f"Pinned Waveshare library {library} contained no source/header files"
                    )

        lib_root.mkdir(parents=True, exist_ok=True)
        for library in ("es8311", "es7210"):
            destination = lib_root / library
            staged = staging / library
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(staged, destination)
        marker.write_text(commit + "\n", encoding="utf-8")
