# KoalaByte Blue Ultra Vision (optional)

Ultra Vision adds an operator-triggered camera snapshot and generic, on-device object detection to the Pi 5 host. It is **optional** and does not change ESP32-S3 or Heltec T114 firmware.

## Hardware and model

- Use a USB UVC camera connected to the Pi 5. A Pi Camera Module may need a Picamera2 adapter in a future hardware-specific integration; the initial implementation targets cameras exposed by OpenCV.
- Install optional dependencies in the KoalaByte virtual environment only after reviewing their size and wheel compatibility on your OS:
  ```bash
  ./pi-companion/.venv/bin/pip install -r requirements-vision.txt
  ```
- Supply an already-present local model file. No model weights are automatically downloaded:
  ```bash
  export KOALABYTE_VISION_MODEL=/opt/koalabyte/models/your-object-model.pt
  PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py status
  ```
  The model should be compatible with the installed Ultralytics runtime. Model installation/licensing is the operator's responsibility.

## Use

Capture one frame and infer generic object categories in memory; nothing is saved unless explicitly requested:

```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py capture --camera-index 0 --model /opt/koalabyte/models/your-object-model.pt
```

Explicitly save a local frame and append detections to the local JSONL log:

```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py capture \
  --camera-index 0 --model /opt/koalabyte/models/your-object-model.pt \
  --site-label "authorized site survey" --save-frame --record
```

Outputs are stored under `logs/ultra_vision/`; image capture is opt-in. `--site-label` is operator-entered text, not a GPS lookup. The initial feature intentionally has no automatic GPS tagging, live-stream recording, background monitoring, or automatic linkage to Kruisin' Wi-Fi/BLE scan rows.

## Camera-awareness workflow

Use **Boomerang** for manual review of cameras personally observed from a lawful public vantage point or described by public records. Vision results are generic object detections, not a verified make/model or proof that an object is a Flock/ALPR camera. An operator must verify any camera observation before entering it in Boomerang. Do not use nearby radio identifiers to infer camera locations or owners.

## Privacy and resource controls

- One frame per explicit command; no continuous recording or automatic tracking.
- No face recognition, person re-identification, license-plate OCR, or identity matching.
- No Wi-Fi/BLE scan, device-address import, external upload, or network request in the vision module.
- CPU inference only in the initial implementation. Benchmark memory, thermal behavior, and latency on the actual Pi 5 before considering an accelerator or continuous mode.
- Keep raw images local and save only when explicitly requested. Follow applicable privacy and recording laws and obtain permission for private spaces.

## Validation

```bash
PYTHONPATH=pi-companion python3 scripts/check_ultra_vision.py
```

This is a hardware-free source-contract check; it does not prove a camera, model, or inference backend works on a physical Pi.
