# KoalaByte Blue Ultra Edition — Consumer User Manual (Jungle Edition)

> **Edition:** KoalaByte Blue **Ultra Edition**  
> **Style:** Jungle/Jumanji-inspired palette with cyberpunk blue, violet, and neon-green accents.  
> **Target profile:** Raspberry Pi 5 (8 GB recommended for the Ultra profile), ESP32-S3 DualEye, and Heltec T114. Optional camera and InnoMaker USB-to-CAN accessories are not assumed to be included.

This manual describes the documented software architecture and gives safe first-run and troubleshooting steps. Some Ultra-branch features remain source-level changes that require validation on the physical target. A documented option is not proof that every hardware configuration has been tested.

## 1. Know the system

- **Raspberry Pi:** owns the companion runtime, menu/action dispatch, AI integration, and optional HDMI display.
- **ESP32-S3 DualEye:** dedicated eyes/face and interaction board. Exact behavior depends on installed firmware and audio configuration.
- **Heltec T114:** nRF52840-based board used by this project for BLE-related functions and the small color mouth/display interface.
- **Sony IMX500 AI Camera:** the designated Ultra camera, connected by the Pi camera ribbon connector. The Pi-side sensor firmware/runtime is installed with `bash scripts/setup_imx500_camera.sh`; the MCU boards do not need camera-specific firmware changes.
- **Optional InnoMaker USB-to-CAN adapter:** used through Linux SocketCAN; it is not flashed by KoalaByte.

## 2. First boot and update

Use a stable Raspberry Pi OS installation and a data-capable USB cable for connected boards. Keep ventilation clear and use a suitable Pi 5 power supply for the attached peripheral load.

```bash
cd ~/KoalaByte-Blue
git checkout koalabyte-blue-ultra
git pull --ff-only origin koalabyte-blue-ultra
```

Read `README-ULTRA.md` and relevant guides before installing or flashing. The canonical installer entry point is `bash one-shot-install.sh`. Back up private settings before updates.

Readiness checks:

```bash
python3 scripts/discover_koalabyte_ports.py --profile heltec
python3 scripts/preflight_all_hardware.py --profile heltec
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
```

Discover serial ports instead of assuming that a device always appears under the same `/dev/ttyACM*` name.

## 3. Menu, voice and displays

The Pi-owned menu is the primary action dispatcher. Input from physical controls, voice, or HDMI should route through that menu. Avoid opening the ESP32 or Heltec serial port from multiple programs at once.

The project documents “Killer Koala” and “Hey Killer Koala” as wake phrases for the DualEye path. The eyes, mouth, and Koalagotchi scenes depend on firmware, bridge services, and the current runtime state.

If an action does nothing:
1. Check menu/action readiness and the relevant service status.
2. Confirm the board is detected and its stable alias exists.
3. Inspect service logs for protocol errors or serial-port ownership conflicts.
4. Capture the error before restarting services; do not repeatedly flash firmware without identifying the failure layer.

## 4. HDMI display mode

The HDMI compositor can show eyes, mouth, menu, Koalagotchi/action scenes, speech motion and alarms. Switching HDMI presentation is designed not to stop the voice bridge, menu actions, or connected boards; verify on your own installation.

```bash
cd ~/KoalaByte-Blue
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py status
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py koalabyte
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py desktop
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py toggle
```

The project documents F12 or the “PI OS” control to release HDMI to Raspberry Pi OS. Arrow keys/WASD navigate, Enter selects, M returns to the main menu, and Escape goes back. On Raspberry Pi OS Lite, desktop mode reveals the console unless a graphical desktop is installed.

For a blank display:

```bash
systemctl status koalabyte-hdmi.service --no-pager -l
journalctl -u koalabyte-hdmi.service -n 100 --no-pager
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/check_hdmi_display.py
```

## 5. AI setup and privacy

Local AI is the default documented mode and uses Llama 3.2 3B (`llama3.2:3b`) as the base for the KillerKoala persona model. Online AI is opt-in and may incur provider charges. Online prompts—and camera frames when online vision is configured—are sent to the hosted provider.

Use **Settings → AI → Configure Online AI Key** or the terminal utility:

```bash
cd ~/KoalaByte-Blue
python3 scripts/koalabyte_ai_key.py setup
python3 scripts/koalabyte_ai_key.py status
python3 scripts/koalabyte_ai_key.py test
python3 scripts/koalabyte_ai_key.py remove
```

The default local persona model is `killerkoala-llama3.2:latest`. The documented key location is `/etc/koalabyte-blue/killerkoala.env` with restrictive permissions. Never commit keys, put them in firmware, paste them into chat, or include them in screenshots/logs. A key-validation request may count as provider usage. Check the active mode before troubleshooting; the documented behavior does not silently fall back from online to local when hosted inference fails.

## 6. Sony IMX500 AI camera and CAN adapter

The designated Ultra camera is the **12.3 MP Sony IMX500 Intelligent Vision Sensor** with onboard neural-network acceleration and RP2040 management. It connects to the Pi camera ribbon connector, not USB UVC. The advertised modes are 4056×3040 at up to 10 fps and 2028×1520 at up to 30 fps, with a 76° field of view and manually adjustable focus. Exact modes depend on the camera/OS configuration.

With the Pi powered off, connect the supplied ribbon cable with the correct orientation. Then run:

```bash
cd ~/KoalaByte-Blue
bash scripts/setup_imx500_camera.sh
# Reboot when convenient, then:
rpicam-hello --list-cameras
rpicam-hello -t 5000
```

The setup script installs the Raspberry Pi OS `imx500-all` and `python3-picamera2` packages and checks the sensor firmware files. First sensor/model loading may take several minutes. Test on-sensor MobileNet inference using the official IMX500 post-processing configuration installed by the OS; see [IMX500 camera notes](IMX500_AI_CAMERA.md).

**Integration status:** Ultra Vision now includes a Picamera2 CSI capture backend alongside USB UVC. Set `KOALABYTE_VISION_CAMERA_BACKEND=picamera2` and `KOALABYTE_VISION_CAMERA_INDEX=0` in `/etc/koalabyte-blue/killerkoala.env`, then restart `koalabyte-dualeye-voice-bridge.service`. A spoken visual request captures one still frame; it is not a continuous stream. Local AI keeps image inference on the Pi's configured local Ollama endpoint. Online AI image upload is separately blocked unless `KILLERKOALA_ONLINE_VISION_ENABLED=true` is explicitly set, in addition to online mode and a valid key. Source changes are committed, but the physical IMX500 camera and full voice round-trip still require testing on the target Pi.

The InnoMaker adapter is used through Linux SocketCAN. Start with interface inventory and isolated bench testing:

```bash
bash scripts/setup_can0.sh --interface can0 --bitrate 500000
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory --interface can0
```

Keep CAN experiments on an isolated bench simulator. Do not connect experimental transmit traffic to a vehicle or live system. Follow the repository's explicit simulator/confirmation gates.

## 8. Firmware and recovery

Do not flash a board solely because a screen is blank. Confirm board identity, port, firmware target and bootloader variant first. Never interrupt power during flashing.

- **ESP32-S3 DualEye:** use the repository flashing script and the discovered port. Successful upload is not proof that eyes, buttons, audio and Pi bridge all communicate correctly.
- **Heltec T114:** use the matching T114 release and its board-specific recovery guide. Confirm the device/bootloader identity before using a UF2 package.

After updating, rerun readiness checks, confirm services and aliases, then test eyes, mouth, buttons, voice and HDMI independently.

## 9. Troubleshooting quick reference

| Symptom | First checks |
|---|---|
| Eyes do not change | DualEye alias, bridge service, queue/log errors, firmware/host protocol compatibility |
| T114 stays idle or blank | USB data cable, detected port, firmware identity, mouth service logs |
| HDMI blank | HDMI service/logs, display backend, video/render/input group membership |
| Online AI unavailable | Active mode, key status (without revealing key), network and provider response |
| IMX500 camera not found | Ribbon orientation/seating, `rpicam-hello --list-cameras`, `imx500-all` package and sensor firmware files |
| CAN interface missing | USB enumeration and SocketCAN setup; isolated bench only |

## Safety and responsible use

Use BLE, GNSS, RF and CAN features only on systems you own or are authorized to test. Respect privacy, consent, local law and provider terms. Do not publish API keys, personal location logs or camera imagery without consent.

## Documentation

Repository: https://github.com/greatwhitek9-lab/KoalaByte-Blue  
Branch: `koalabyte-blue-ultra`  
Start with `README-ULTRA.md`, `docs/HDMI_DISPLAY.md`, `docs/FLASHING.md`, and the relevant component guide.

**Visual asset note:** the consumer PDF uses the supplied Jungle Edition cover reference. The repository currently lacks a verified photo set for all components, so it does not misrepresent concept artwork as real product photography. Add verified photographs of the exact hardware in a future visual revision.
