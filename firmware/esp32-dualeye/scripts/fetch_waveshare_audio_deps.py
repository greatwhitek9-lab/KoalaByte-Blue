Import("env")
from pathlib import Path
import shutil, tempfile, urllib.request, zipfile

project = Path(env.subst("$PROJECT_DIR"))
vendor = project / "lib" / "waveshare_audio"
commit = "f16371ca7b7d4e17de6d6f6ea293981b37c0ca51"
marker = vendor / ".waveshare-audio-f16371c"
archive = f"https://github.com/waveshareteam/ESP32-S3-DualEye-Touch-LCD-1.28/archive/{commit}.zip"
root = f"ESP32-S3-DualEye-Touch-LCD-1.28-{commit}/example/ESP32-S3-DualEye-LCD-1.28/Arduino-3.2.0/libraries"

if not marker.exists():
    print("Fetching pinned Waveshare ES8311/ES7210 drivers")
    if vendor.exists():
        shutil.rmtree(vendor)
    vendor.mkdir(parents=True)
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
                    output = vendor / library / name[len(prefix):]
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, output.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
    marker.write_text(commit + "\n", encoding="utf-8")
