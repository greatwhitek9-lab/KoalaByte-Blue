# Heltec T114 hardware validation

Use this checklist before flashing or running the canonical Heltec Edition branch on physical hardware.

## 1. Confirm the canonical branch

```bash
git checkout koalabyte_blue_v2_heltec_edition
python3 scripts/check_repo_readiness.py
```

The installer should not require the short `heltec` branch alias.

## 2. Confirm USB devices

Connect the Raspberry Pi, ESP32-S3 DualEye, Heltec T114, and InnoMaker USB-CAN adapter with data-capable USB cables.

```bash
lsusb
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
python3 scripts/discover_koalabyte_ports.py --profile heltec
```

Expected stable paths after udev install:

```text
/dev/koalabyte-esp32-eyes
/dev/koalabyte-heltec
/dev/koalabyte-nrf-ble
```

## 3. Install stable udev paths

```bash
bash scripts/install_koalabyte_udev_rules.sh
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug/replug the USB devices after installing rules.

## 4. Build-only preflight

Normal firmware stack:

```bash
BUILD_ONLY=1 bash scripts/flash_all_components.sh --all
```

Optional Koala Konnect / T114 HCI USB profile:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect --build-only
```

## 5. CAN validation

The InnoMaker CAN adapter uses Linux SocketCAN. The adapter itself is not flashed.

```bash
CAN_INTERFACE=can0 CAN_BITRATE=500000 bash scripts/setup_can0.sh
python3 scripts/run_koala_kan_kommander.py manifest --interface can0
python3 scripts/run_koala_kan_kommander.py inventory --interface can0
python3 scripts/run_koala_kan_kommander.py status --interface can0
```

For local software-only testing:

```bash
bash scripts/setup_vcan0.sh
python3 scripts/run_koala_kan_kommander.py status --interface vcan0
```

## 6. Flash normal runtime profile

```bash
bash scripts/flash_all_components.sh --install-firmware
```

This installs the Pi companion, ESP32 DualEye firmware, Heltec mouth/GNSS/BLE-primary firmware, BLE node manager service, and CAN checks.

## 7. Flash optional Koala Konnect profile only when needed

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect
```

This replaces the normal Heltec mouth/GNSS/BLE-primary firmware until you flash the normal profile back.

## 8. Hardware safety checks

- Use data-capable USB cables.
- Keep Pi GPIO at 3.3 V logic only.
- Do not wire Heltec TX/RX to the Pi GPIO header for the USB CDC runtime path.
- Do not connect CAN to a real vehicle network. Use an isolated bench harness or simulator.
- Use the correct antenna connector for each radio path.
- Use a proper BMS/charger and regulated 5 V supply for battery-powered builds.
