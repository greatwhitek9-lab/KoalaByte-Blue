# KoalaByte Blue Ultra — Raspberry Pi 5 (8 GB)

**Target platform:** Raspberry Pi 5, 8 GB RAM, 64-bit Raspberry Pi OS Bookworm or Trixie.  
**Branch:** `koalabyte-blue-ultra` (Git refs cannot contain spaces).  
**Base:** `Main` from KoalaByte Blue.  
**Scope:** Pi 5 host upgrades; preserve the ESP32-S3 DualEye and Heltec T114 firmware/protocol contracts.

> **Port status:** This branch contains Pi 5 host-profile and adaptive-resource source changes. It has not yet been verified on the physical target Pi 5. Run the hardware-free profile tests and deployment check gates before installing or flashing anything.

## Ultra upgrade ledger

| Area | Change in this branch | Validation status |
|---|---|---|
| Host support | Pi 5 is explicitly recognized in the 64-bit host preflight; Pi 3B+, Pi 4, Pi 400, Pi 500 and Pi 5 remain recognized. | Source change; run host gate on target |
| Hardware-aware budgets | Canonical `pi_runtime_profile.py` detects model, RAM, CPU count and emits AI, HDMI, worker/build and power recommendations. | Hardware-free profile tests available |
| Local AI | Pi 5 with at least 7,000 MiB detected RAM recommends a 2,048-token context, up to two parallel requests, one loaded model, 300-second keep-alive and 160-token output budget. A temporary profile-specific Modelfile applies context/output limits without editing the checked-in Pi 3-safe source. Explicit environment overrides win. | Recommendation; smoke-test on hardware |
| Local response sizing | Response length is tuned by detected RAM tier to avoid long generations on lower-memory Pis while allowing more headroom on Pi 5 8 GB. | Source change; measure latency on target |
| HDMI / Koalagotchi | Renderer selects synchronized frame budgets by Pi generation/RAM. Pi 5 8 GB targets up to 60 FPS; 4 GB Pi 5 targets 45 FPS; 2 GB Pi 5 targets 30 FPS. Wayland/X11 is preferred when available, with SDL KMS/DRM fallback. | Source change; display backend must be tested on target |
| Processing | Profile recommends up to four runtime workers and up to four firmware build jobs for Pi 5 8 GB; lower-memory systems get more conservative build budgets. Swap target and thermal policy are reported, not silently applied by profile detection. | Profile output; benchmark on target |
| Optional Ultra Vision | USB/UVC camera capture and local object detection; opt-in protected GNSS tagging, operator-supplied Kruisin event/session references, and confidence-scored camera-like candidates for manual verification. No automatic RF-to-photo matching. | Source-contract check; camera/model/GNSS must be tested on hardware |
| Power and thermal safety | No overclock is introduced. Existing deployment power gate remains in force; a current or latched under-voltage condition must be cleared before hardware writes. Official Pi 5 27 W / 5 V 5 A supply is recommended for full peripheral load. | Must verify on target |
| MCU compatibility | ESP32-S3 and Heltec T114 sources, identities, serial ownership, and protocols are intentionally preserved. | Must run existing source and firmware gates |
| Validation and CI | Hardware-free fixtures cover Pi 5 2/4/8/16 GB and Pi 3B+ resource tiers; the profile is included in dependency and installer-contract checks. | Checks are committed; execution results must be confirmed in CI/on hardware |
| Documentation | This branch-specific README records the Ultra profile and its validation status; detailed technical notes live in `docs/PI5_ULTRA.md`. | Added |

## Optional add-ons: AI camera and InnoMaker USB-to-CAN

**KillerKoala supports two AI modes.** `local` (default) runs downloaded Ollama models on the Pi and does not require paid LLM tokens. KoalaByte Blue Ultra defaults to the local **Llama 3.2 3B** model (`llama3.2:3b` base, `killerkoala-llama3.2:latest` KillerKoala persona alias) instead of TinyLlama. `online` is an explicit opt-in to Ollama Cloud and requires an Ollama API key; cloud usage may be billed according to Ollama's current terms. Online mode sends prompts—and, if online vision is enabled, camera frames—to Ollama's hosted service. The companion does not silently switch modes when local inference fails. Model downloads need internet access and storage; local inference also uses electricity and Pi resources. See [Ollama's local API documentation](https://github.com/ollama/ollama/blob/main/docs/api/introduction.mdx) and [Ollama Cloud documentation](https://github.com/ollama/ollama/blob/main/docs/cloud.mdx).

These add-ons are optional. Install and validate them independently after the base KoalaByte Blue Ultra system is stable. The camera path does not require MCU firmware changes. The InnoMaker adapter remains on its stock firmware and is used through Linux SocketCAN.

### Choose local or online AI

KillerKoala defaults to `local` Ollama inference, which does not require paid LLM tokens. Online mode is an explicit opt-in to Ollama Cloud and may incur provider charges. The ESP32 menu is supplied by the Pi, so use the Pi's Settings menu to change the active mode:

**Settings → AI → Online AI ON / Online AI OFF**

- **AI Mode Status** shows the active mode and whether an API key is configured.
- **Online AI ON** updates the private setting and restarts the KillerKoala voice bridge. It fails safely if no API key is configured.
- **Online AI OFF** switches back to local Ollama and restarts the bridge. There is no automatic online fallback.

Configure the key through either supported setup path—there is no need to edit the private environment file by hand.

**HDMI / menu setup:** Open **Settings → AI → Configure Online AI Key**. Enter the key with the physical keyboard or the on-screen keyboard controls; characters are masked. Voice dictation is disabled for this field. KoalaByte validates the key with a minimal authenticated Ollama Cloud request before saving it. That test sends a short prompt and may count as provider usage.

**Terminal setup:**

```bash
cd ~/KoalaByte-Blue
python3 scripts/koalabyte_ai_key.py setup
python3 scripts/koalabyte_ai_key.py status
python3 scripts/koalabyte_ai_key.py test
```

The terminal utility uses hidden input and asks you to repeat the key. To remove the key:

```bash
python3 scripts/koalabyte_ai_key.py remove
```

The saved key is stored only in `/etc/koalabyte-blue/killerkoala.env`, with mode `0600`; the helper is root-owned, and a restricted sudoers rule grants only the required key-management operations. The key is never stored in ESP32 firmware, printed in status output, or committed to Git. **Settings → AI** also contains **Test API Key**, **API Key Status**, and **Remove API Key**. Removing the key automatically returns to local AI if online mode was active.

Online AI uses Ollama Cloud and may incur provider charges. The key test sends one minimal model request; it is not a zero-usage authentication-only check. If the menu does not show the new options, update branch `koalabyte-blue-ultra`, rerun `bash scripts/install_esp32_dualeye_voice_bridge_service.sh`, and restart the menu UI.

When online mode is active, prompts are sent to Ollama Cloud. If online vision is configured, explicit visual requests also send the captured camera frame to the hosted service. Leave online vision blank or switch to local mode if you do not want camera images sent off-device.

### A. Optional AI camera — KillerKoala conversational vision

**What it does:** With a compatible USB UVC camera and a configured local or hosted Ollama multimodal model, KillerKoala can answer explicit visual requests such as “what do you see?”, “look at this”, or “describe the scene.” Each request captures one still frame; it is not a continuous stream. The camera frame is held in memory and is not saved by the conversational path.

**Hardware and prerequisites**

- Raspberry Pi 5 running the `koalabyte-blue-ultra` branch and the normal KoalaByte virtual environment.
- Sony IMX500 CSI AI Camera or a USB UVC camera; select `KOALABYTE_VISION_CAMERA_BACKEND=picamera2` for the CSI camera.
- Local Ollama installation and enough free RAM/storage for the vision model. A 7B vision model may be slow or memory-intensive on an 8 GB Pi 5, especially if the regular KillerKoala model is loaded at the same time.
- Camera permission and a suitable view; test with a non-sensitive scene first.

**Install and enable**

1. Open a terminal on the Pi and enter the Ultra checkout:
   ```bash
   cd ~/KoalaByte-Blue
   git checkout koalabyte-blue-ultra
   git pull --ff-only origin koalabyte-blue-ultra
   ```

2. Install the optional camera/inference dependencies into KoalaByte's virtual environment:
   ```bash
   ./pi-companion/.venv/bin/pip install -r requirements-vision.txt
   ```

3. Confirm Linux can see the camera. If available, install the small diagnostic utility and list video devices:
   ```bash
   sudo apt-get update
   sudo apt-get install -y v4l-utils
   v4l2-ctl --list-devices
   ls -l /dev/video*
   ```
   Use camera index `0` unless the camera appears at another index. If the device is absent, try a data-capable USB cable/port and check `dmesg --follow` while reconnecting it. The IMX500/CSI camera uses the Picamera2 backend; USB webcams use UVC.

4. Install a compatible vision model into local Ollama. Example:
   ```bash
   ollama pull llava:7b
   ollama list
   ```
   Model choice is operator-controlled. Check model license, storage requirements, RAM use, response latency, and thermal behavior before keeping it enabled. Do not assume the example model will perform well under concurrent load on every Pi 5.

5. Enable vision in the private service environment file:
   ```bash
   sudoedit /etc/koalabyte-blue/killerkoala.env
   ```
   Add or set this line (without `#`):
   ```bash
   KILLERKOALA_VISION_MODEL=llava:7b
   ```
   Keep this file private; do not put credentials or personal data into Git. Leave the model value blank to disable camera vision. Local mode uses loopback Ollama; online mode is allowed only after the explicit opt-in and API-key setup above.

6. Restart the voice bridge so it reads the setting:
   ```bash
   sudo systemctl restart koalabyte-dualeye-voice-bridge.service
   systemctl --no-pager --full status koalabyte-dualeye-voice-bridge.service
   ```

7. Run the source-contract check, then ask KillerKoala an explicit visual question through the normal voice path:
   ```bash
   PYTHONPATH=pi-companion python3 scripts/check_ultra_vision.py
   ```
   Example voice requests: “KillerKoala, what do you see?”, “KillerKoala, look at this”, or “describe the scene.” The source check does not prove physical camera capture or model inference; confirm those on the actual Pi.

**Direct capture / local code entry points**

To check the camera/detector backend without starting conversational voice:
```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py status
```

For a one-frame object-detection run, first provide a model file compatible with the installed Ultralytics runtime. Model weights are not downloaded automatically by this command:
```bash
export KOALABYTE_VISION_MODEL=/opt/koalabyte/models/your-object-model.pt
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_ultra_vision.py capture \
  --camera-index 0 --model "$KOALABYTE_VISION_MODEL"
```

Relevant implementation files:
- `pi-companion/koalablue/ultra_vision.py` — camera capture, local object detection, conversational vision backend and privacy guards.
- `pi-companion/koalablue/killerkoala_hybrid_companion.py` — routes explicit visual questions to camera vision.
- `pi-companion/koalablue/killerkoala_voice_control.py` — voice intent routing.
- `scripts/run_ultra_vision.py` — command-line entry point.
- [Full Ultra Vision notes](docs/ULTRA_VISION.md).

**Privacy and troubleshooting**

- Capture happens only after an explicit visual request. No background monitoring, covert capture, or continuous recording is enabled.
- Conversational frames are not saved. The separate CLI saves images/logs only when its explicit save/record flags are supplied.
- The system must not identify people, read license plates, track people/vehicles, or infer a Wi-Fi/BLE emitter's location from an image.
- If KillerKoala says vision is unavailable, check `v4l2-ctl --list-devices`, `ollama list`, the model setting, and `journalctl -u koalabyte-dualeye-voice-bridge.service -n 100 --no-pager`. Confirm the Ollama service is active with `systemctl status ollama.service`.
- If RAM use, latency, or temperature is excessive, disable vision by blanking `KILLERKOALA_VISION_MODEL` and restarting the voice bridge.

### B. Optional InnoMaker USB-to-CAN adapter — Koala Kan Kommander

**What it does:** The InnoMaker USB-to-CAN adapter exposes a Linux SocketCAN interface (commonly `can0`) for authorized CAN bench observation, synthetic test payloads, and reporting. It is optional and separate from the ESP32-S3 and Heltec T114 serial links. The installer does not flash the adapter or transmit CAN frames during setup.

**Safety and wiring first**

- Use only an isolated CAN simulator or an owned, authorized bench harness for the documented Koala Kan Kommander workflow. Do not connect this setup to a live vehicle, safety-critical system, battery-management network, or industrial controller.
- Connect the adapter to a Pi USB data port. Connect CAN_H, CAN_L, and GND only to the matching terminals on the isolated bench equipment, following the exact InnoMaker kit's manual. Do not wire CAN_H/CAN_L to Raspberry Pi GPIO. Check bus termination and the bench's required bitrate before bringing the interface up.
- Adapter models/firmware revisions can differ. The setup script expects the Linux `gs_usb`/SocketCAN driver path; verify the exact model against the [InnoMaker USB2CAN documentation](https://github.com/INNO-MAKER/usb2can) and [product documentation](https://www.inno-maker.com/product/usb-can/).

**Install and detect**

1. Connect the InnoMaker adapter and isolated bench wiring, then enter the Ultra checkout:
   ```bash
   cd ~/KoalaByte-Blue
   git checkout koalabyte-blue-ultra
   git pull --ff-only origin koalabyte-blue-ultra
   ```

2. Install the Linux SocketCAN tools:
   ```bash
   sudo apt-get update
   sudo apt-get install -y can-utils iproute2 usbutils
   ```

3. Ask the KoalaByte helper to load the standard Linux CAN modules, wait for the adapter, and configure `can0` at 500 kbit/s (change the bitrate only to match the bench equipment):
   ```bash
   CAN_INTERFACE=can0 CAN_BITRATE=500000 \
     bash scripts/setup_can0.sh --interface can0 --bitrate 500000
   ```
   The helper writes diagnostic artifacts to `logs/koala_kan_kommander/`. It does not flash adapter firmware. If the interface is not found, inspect `lsusb`, `dmesg | tail -n 100`, and `ip -details link show`; do not install a random kernel driver or firmware image without confirming the exact adapter revision.

4. Verify the Linux interface:
   ```bash
   ip -details -statistics link show can0
   PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
     scripts/run_koala_kan_kommander.py inventory
   PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
     scripts/run_koala_kan_kommander.py status --interface can0
   ```

5. If you want the one-shot installer to include the optional CAN service, plug in the adapter before deployment and use auto-detection (the default). To request it explicitly:
   ```bash
   INSTALL_INNOMAKER_CAN=1 KOALABYTE_SERVICE_USER="$(whoami)" \
     bash one-shot-install.sh
   ```
   This enables CAN interface setup/service integration; it does not authorize CAN transmission. For a Pi-only non-writing contract check with the adapter omitted:
   ```bash
   INSTALL_INNOMAKER_CAN=0 KOALABYTE_SERVICE_USER="$(whoami)" \
     bash one-shot-install.sh --check-only
   ```

**Use the menu and CLI**

The menu path is **CAN Bench Tools → Koala Kan Kommander**. Start with inventory/status and a bounded listen on an isolated, correctly terminated simulator:
```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
  scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
  scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
  scripts/run_koala_kan_kommander.py report --interface can0
```

Generate synthetic data without transmitting it:
```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
  scripts/run_koala_kan_kommander.py generate-payloads \
  --interface can0 --payload-profile all --base-id 0x600 \
  --sequence-count 8 --tag KOALAKAN
```

The transmit interface is strictly limited to synthetic lab-range frames and requires both `--bench-simulator` and `--confirm-transmit`; the permitted standard 11-bit ID range is `0x600–0x67F`, and batches are capped. Use that gated path only with an isolated simulator—not a vehicle or operational control network. For example, on the isolated simulator only:
```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
  scripts/run_koala_kan_kommander.py transmit \
  --interface can0 --bench-simulator --confirm-transmit \
  --payload-profile heartbeat --base-id 0x600 --sequence-count 3
```

Relevant implementation files:
- `scripts/setup_can0.sh` — Linux module/interface setup and status artifacts.
- `scripts/install_can0_service.sh` / `scripts/run_can0_service.sh` — optional persistent service.
- `scripts/run_koala_kan_kommander.py` and `pi-companion/koalablue/koala_kan_kommander.py` — menu backend, inventory, bounded listening, synthetic payloads, reports, and gated bench transmit.
- [Koala Kan Kommander technical notes](docs/KOALA_KAN_KOMMANDER_REVA22.md).

**Troubleshooting**

- No `can0`: check `lsusb`, `dmesg`, `lsmod | grep -E 'gs_usb|can_dev|can_raw'`, then rerun `scripts/setup_can0.sh` after confirming the model is supported.
- Interface exists but is `DOWN`: confirm the bench bitrate and termination, then rerun the setup helper with the correct bitrate.
- No frames during listen: confirm the simulator is powered, connected to CAN_H/CAN_L/GND correctly, set to the same bitrate, and terminated appropriately. A silent bus can be normal if no node is transmitting.
- Keep CAN logs and captures local; do not publish sensitive payloads or identifiers.

## Recommended clean install

Use the 64-bit Raspberry Pi OS Bookworm or Trixie image, connect the HDMI display, keyboard, ESP32-S3 and Heltec T114, and join Wi-Fi first. Clone this branch rather than `Main`:

```bash
git clone --branch koalabyte-blue-ultra --single-branch \
  https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
```

Run the hardware-free profile checks and inspect the detected profile:

```bash
PYTHONPATH=pi-companion python3 scripts/check_pi5_ultra_profile.py --check-only
PYTHONPATH=pi-companion python3 scripts/check_pi5_ultra_profile.py --json
```

Run non-writing validation before installation:

```bash
python3 scripts/check_supported_host.py
python3 scripts/check_whole_system_deployment.py --source-only
bash one-shot-install.sh --check-only
```

If those checks pass, run the project's normal deployment procedure. Do not flash either MCU just to test Pi host detection. If a later deployment requests firmware, review the manifest/identity and power preflight first.

## Runtime profile

The canonical detector is `pi-companion/koalablue/pi_runtime_profile.py`. It reads the device-tree model and `/proc/meminfo`; profile detection does not require network access, alter files, change clocks/voltage, or flash firmware. Hardware-free fixtures in `scripts/check_pi5_ultra_profile.py` exercise 2 GB, 4 GB and 8/16 GB Pi 5 profiles and a legacy Pi 3B+ profile.

For a Pi 5 with at least 7,000 MiB detected RAM, the profile recommends:

- Ollama context: 2,048 tokens
- Ollama parallel requests: 1
- Maximum loaded models: 1
- Ollama keep-alive: 300 seconds
- Generated output budget: 128 tokens
- HDMI / Koalagotchi target: up to 60 FPS
- Runtime worker budget: up to four
- Firmware build jobs: up to four
- Build swap target: 1,024 MiB (profile recommendation)

These are starting points, not guarantees of performance. Full documentation remains in [Pi 5 Ultra notes](docs/PI5_ULTRA.md).
