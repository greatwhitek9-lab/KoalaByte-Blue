# KoalaByte Blue Ultra — Sony IMX500 AI Camera

The designated camera hardware for KoalaByte Blue Ultra is the **12.3 MP Sony IMX500 Intelligent Vision Sensor** (Raspberry Pi AI Camera class), connected through the Raspberry Pi camera ribbon connector. It is not a USB UVC webcam.

## Hardware and capability

- Sony IMX500 12.3 MP sensor with an on-sensor neural-network accelerator.
- Integrated low-power inference engine and RP2040 used for neural-network/firmware management.
- The camera product may ship with a MobileNet model; the Raspberry Pi software stack also provides supported prepackaged IMX500 models.
- Sensor modes advertised for this camera: 4056×3040 at up to 10 fps and 2028×1520 at up to 30 fps.
- 76° field of view, manually adjustable focus, supplied 200 mm camera cable(s).

Exact supported modes depend on the camera revision, operating system, sensor configuration and application. The camera ribbon cable must be connected with the correct orientation while the Pi is powered off.

## Install Pi-side runtime and sensor firmware

Run on the target Raspberry Pi, from the Ultra checkout:

```bash
cd ~/KoalaByte-Blue
git checkout koalabyte-blue-ultra
git pull --ff-only origin koalabyte-blue-ultra
bash scripts/setup_imx500_camera.sh
```

The script installs Raspberry Pi OS packages `imx500-all` and `python3-picamera2`, checks the standard IMX500 firmware files, and attempts camera enumeration. It does not flash the ESP32-S3 DualEye or Heltec T114. It does not reboot the Pi automatically.

The official Raspberry Pi package `imx500-all` provides the sensor runtime firmware, prepackaged neural-network model files and camera post-processing stages. First sensor/model loading can take several minutes. Reboot after installation when convenient.

## Verify camera and on-sensor inference

```bash
rpicam-hello --list-cameras
rpicam-hello -t 5000
```

If the camera is detected and the model configuration exists, test the packaged MobileNet SSD inference pipeline:

```bash
test -r /usr/share/rpi-camera-assets/imx500_mobilenet_ssd.json && \
  rpicam-hello -t 10000 \
    --post-process-file /usr/share/rpi-camera-assets/imx500_mobilenet_ssd.json
```

Asset directories may differ across Raspberry Pi OS releases. If the JSON file is absent, inspect the installed `imx500-all`/camera-assets packages and the current official documentation rather than hard-coding a guessed alternate path.

## KoalaByte software integration boundary

There are two separate paths:

1. **On-sensor inference:** IMX500 runs a supported compiled neural-network model and produces inference metadata. Raspberry Pi camera software interprets the output. This is suitable for supported object detection/classification tasks.
2. **Conversational vision:** a natural-language model receives an image frame and produces a description or answer. This is a different operation from MobileNet inference and may use local or explicitly enabled hosted inference.

The Ultra Vision conversational capture path now has a Picamera2 backend alongside the existing OpenCV UVC backend. Set `KOALABYTE_VISION_CAMERA_BACKEND=picamera2` in `/etc/koalabyte-blue/killerkoala.env` for the CSI/IMX500 camera, and set `KOALABYTE_VISION_CAMERA_INDEX=0` (or the enumerated camera number). `auto` prefers Picamera2 when importable; an explicit backend never silently switches. The capture helper requests one still frame, then stops and closes Picamera2 before inference/network activity. This is a source-level integration; physical-camera and end-to-end voice testing are still required before claiming hardware validation. Conversational still-frame capture is separate from the IMX500 on-sensor MobileNet inference pipeline.

## Troubleshooting

- **No camera listed:** power off, reseat ribbon at both ends with contacts correctly oriented, then check `rpicam-hello --list-cameras`.
- **Preview works but inference does not:** verify `imx500-all`, model assets and the exact post-processing JSON path.
- **First run appears stuck:** allow time for the sensor to load firmware/model data; do not disconnect power while it is loading.
- **Package unavailable:** confirm Raspberry Pi OS release and repositories before changing package sources.
- **Conversational vision still reports no camera:** check `KOALABYTE_VISION_CAMERA_BACKEND`, camera index, the `python3-picamera2` package, and service logs. Source integration does not guarantee that a particular camera/OS combination has been physically validated.

## Official reference

Raspberry Pi AI Camera documentation: https://www.raspberrypi.com/documentation/accessories/ai-camera.html
