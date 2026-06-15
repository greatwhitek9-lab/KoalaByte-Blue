# KoalaByte Blue RevA5 Assembly and Flashing Guide

## RevA5 changes

- Adds four external front-panel buttons for the final compact build.
- Keeps Nordic nRF52840 Dongle / PCA10059 as the production BLE board.
- Keeps Nordic nRF52840 DK / PCA10056 as the optional development/debug board.
- Adds Raspberry Pi GPIO button firmware support through `gpiozero`.
- Adds printable front button bezel STL for four 6mm tactile buttons in the downloadable production ZIP.

## Button hardware

The nRF52840 Dongle includes one tiny onboard user button, but it is not enough for a front-panel user interface. The production build now adds:

```text
Adafruit Tactile Button switch (6mm) x 20 pack, Product ID 367
```

Use four buttons from the pack:

```text
Back, Select, Next, Menu
```

## Button wiring

| Button | Pi BCM GPIO | Pi physical pin | Button other side |
|---|---:|---:|---|
| Back | GPIO5 | 29 | GND |
| Select | GPIO6 | 31 | GND |
| Next | GPIO13 | 33 | GND |
| Menu | GPIO19 | 35 | GND |
| Shared ground | GND | 39 | All button grounds |

Each button is normally open. One leg goes to the assigned GPIO pin, and the other leg goes to GND. The software uses internal pull-up resistors.

## Step-by-step button build

1. Print `KoalaByte_Blue_Front_Button_Bezel_4x6mm_RevA5.stl` from the production ZIP.
2. Dry-fit the four tactile switches in the bezel/front panel.
3. Solder or crimp one signal wire to each button.
4. Daisy-chain the other side of all buttons to a shared black GND wire.
5. Connect signal wires to Pi GPIO5, GPIO6, GPIO13, and GPIO19.
6. Connect the shared ground to Pi physical pin 39.
7. Add heat-shrink and strain relief so the button harness cannot pull on the Pi header.
8. Boot the Pi and install requirements:

```bash
cd pi-companion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

9. Run the companion:

```bash
python -m koalablue.app --serial /dev/ttyACM0
```

10. Type:

```text
buttons
```

11. Press each button and verify events are logged in:

```text
pi-companion/logs/gpio_buttons.jsonl
```

## ESP32 flashing

```bash
bash scripts/flash_esp32.sh
```

## Optional nRF52840 DK flashing

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

## Validation checklist

- [ ] Pi boots without undervoltage warning.
- [ ] ESP32 serial JSON boot message is visible.
- [ ] nRF52840 Dongle enumerates on USB.
- [ ] All four front buttons generate GPIO button events.
- [ ] Shared GND bus is secure.
- [ ] Button harness has strain relief.
- [ ] Case closes without pinching wires.
- [ ] 5V rail remains within 5.05 V to 5.15 V under load.
