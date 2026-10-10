# KoalaByte Blue Ultra Vision (optional, Pi 5)

Ultra Vision is an optional camera add-on for the `koalabyte-blue-ultra` branch. It captures one frame per explicit command, performs local CPU object detection, and can attach a recent GNSS fix when the operator opts in. It does not change ESP32-S3 or Heltec T114 firmware.

## Hardware and model

- Initial hardware target: USB UVC camera connected to the Raspberry Pi 5 and exposed through OpenCV. Pi Camera Module support needs a separately validated Picamera2 backend.
- Install optional dependencies in the KoalaByte virtual environment after reviewing wheel compatibility and storage use:
  ```bash
  ./pi-companion/.venv/bin/pip install -r requirements-vision.txt
  ```
- Supply an already-present local model file. Model weights are never downloaded automatically:
  ```bash
  export KOALABYTE_VISION_MODEL=/opt/koalabyte/models/your-object-model.pt
  PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py status
  ```
  The model must be compatible with the installed Ultralytics runtime. Model installation and licensing are the operator's responsibility.

## Capture and identify

Capture a single frame and classify objects in memory. Nothing is saved unless requested:

```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py capture \
  --camera-index 0 --model /opt/koalabyte/models/your-object-model.pt
```

Explicitly save a local image and append the event/detections to a local JSONL log:

```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py capture \
  --camera-index 0 --model /opt/koalabyte/models/your-object-model.pt \
  --site-label "authorized street-side observation" --save-frame --record
```

Files are stored under `logs/ultra_vision/`. Images are not saved by default. The site label is operator-entered text; it does not locate a device.

## Koala Kombat Kruisin and GNSS context

During an authorized Kruisin survey, a user may explicitly request a camera capture and pass a session/event or survey-row reference:

```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py capture \
  --camera-index 0 --model /opt/koalabyte/models/your-object-model.pt \
  --geotag --session-id "kruisin-session-01" \
  --event-id "street-observation-01" --observation-ref "survey-row-17" \
  --save-frame --record
```

- `--geotag` is opt-in. It uses the existing protected GNSS path and does not open the Heltec serial port directly.
- Only a valid fix with a timestamp no older than 120 seconds is attached. If the protected location gate is locked, the fix is absent, coordinates are invalid, or the fix is stale, the event records location as unknown.
- `--session-id`, `--event-id`, and `--observation-ref` are operator-supplied labels. The module does not import Wi-Fi/BLE MAC addresses or automatically match radio records to photos.
- A survey-row reference is contextual correlation only. It is **not proof** that a Wi-Fi/BLE emitter is physically at the photographed location; GNSS describes the camera/operator position at capture time, not the emitter's location.
- Geotagged images and survey logs can reveal sensitive locations. Keep logs local, set retention limits, and redact location and radio identifiers before sharing/exporting.

## Spotting camera-like objects

Use `--camera-spotting` to flag detections whose model-provided labels look like a camera category:

```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py capture \
  --camera-index 0 --model /opt/koalabyte/models/your-object-model.pt \
  --camera-spotting --save-frame --record
```

The output marks candidate detections with a confidence score and `unverified model suggestion`. This is generic object classification—not verified identification of a Flock, ALPR, security-camera make/model, owner, or function. The operator must review the image and confirm an observation before treating it as verified. Do not infer camera locations or owners from nearby Wi-Fi/BLE identifiers.

## Privacy and resource controls

- One frame per explicit command; no continuous recording, background monitoring, covert capture, or remote activation.
- No face recognition, person re-identification, license-plate OCR, identity matching, or automatic following of people/vehicles.
- No Wi-Fi/BLE scan, device-address import, automatic radio-to-image correlation, external upload, or network request in the vision module.
- CPU inference only. Benchmark latency, memory, and thermal behavior on the actual Pi 5 before considering an accelerator.
- Save locally only when `--save-frame` or `--record` is explicitly passed. Follow applicable privacy/recording laws and obtain permission for private spaces.

## Validation

```bash
PYTHONPATH=pi-companion python3 scripts/check_ultra_vision.py
```

This is a hardware-free source-contract check. It does not prove a camera, model, or inference backend works on a physical Pi 5.
