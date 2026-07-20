Import("env")
from pathlib import Path
import shutil, tempfile, urllib.request, zipfile

project = Path(env.subst("$PROJECT_DIR"))
lib_root = project / "lib"
commit = "f16371ca7b7d4e17de6d6f6ea293981b37c0ca51"
marker = lib_root / ".waveshare-audio-f16371c"
archive = f"https://github.com/waveshareteam/ESP32-S3-DualEye-Touch-LCD-1.28/archive/{commit}.zip"
root = f"ESP32-S3-DualEye-Touch-LCD-1.28-{commit}/example/ESP32-S3-DualEye-LCD-1.28/Arduino-3.2.0/libraries"

framework = Path(env.PioPlatform().get_package_dir("framework-arduinoespressif32"))
network_source = framework / "libraries" / "Network" / "src"
if network_source.exists():
    env.Append(CPPPATH=[str(network_source)])
    # pioarduino 55.x discovers Arduino 3 Network headers for WiFi but omits the
    # Network source archive from the final link. Mirror the exact framework
    # source tree into a project library; these are unmodified framework files.
    network_library = lib_root / "arduino_network_runtime" / "src"
    if network_library.exists():
        shutil.rmtree(network_library)
    shutil.copytree(network_source, network_library)

# ESP_SR includes ESP_I2S.h from another framework library. PlatformIO's deep
# dependency scanner finds ESP_SR but does not reliably propagate that sibling
# framework-library include directory while compiling ESP_SR itself.
esp_i2s_source = framework / "libraries" / "ESP_I2S" / "src"
if esp_i2s_source.exists():
    env.Append(CPPPATH=[str(esp_i2s_source)])
else:
    raise RuntimeError(f"Arduino ESP_I2S headers not found: {esp_i2s_source}")

if not marker.exists():
    print("Fetching pinned Waveshare ES8311/ES7210 drivers")
    stale = lib_root / "waveshare_audio"
    if stale.exists():
        shutil.rmtree(stale)
    for library in ("es8311", "es7210"):
        destination = lib_root / library
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dualeye-audio-") as temp:
        zip_path = Path(temp) / "waveshare.zip"
        urllib.request.urlretrieve(archive, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            for library in ("es8311", "es7210"):
                prefix = f"{root}/{library}/"
                names = [n for n in zf.namelist() if n.startswith(prefix) and not n.endswith("/")]
                if not names:
                    raise RuntimeError(f"Missing Waveshare library {library}")
                for name in names:
                    output = lib_root / library / name[len(prefix):]
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, output.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
    marker.write_text(commit + "\n", encoding="utf-8")
