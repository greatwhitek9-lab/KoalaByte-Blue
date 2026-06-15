# KoalaByte Blue RevA6 Six-Button Assembly and Flashing Guide

## RevA6 changes

- Expands the front-panel control layout from four buttons to six buttons.
- Numbers buttons **1 through 6 from left to right** across the front panel.
- Keeps Nordic nRF52840 Dongle / PCA10059 as the production BLE board.
- Keeps Nordic nRF52840 DK / PCA10056 as the optional development/debug board.
- Adds Raspberry Pi GPIO button firmware support through `gpiozero`.
- Adds hold behavior: Button 3 normal press is Enter/Select; hold for 3 seconds produces a Shutdown command event.

## Button hardware

The nRF52840 Dongle includes one tiny onboard user button, but it is not enough for a front-panel user interface. The production build uses:

```text
Adafruit Tactile Button switch (6mm) x 20 pack, Product ID 367
```

Use six buttons from the pack:

```text
1 Main Menu | 2 Left/Back | 3 Enter/Select + hold Shutdown | 4 Right/Forward | 5 Up | 6 Down
```

## Button wiring

| Button # | Function | Pi BCM GPIO | Pi physical pin | Button other side |
|---:|---|---:|---:|---|
| 1 | Main Menu | GPIO5 | 29 | GND |
| 2 | Move Left / Back | GPIO6 | 31 | GND |
| 3 | Enter / Select; hold for Shutdown | GPIO13 | 33 | GND |
| 4 | Move Right / Forward | GPIO19 | 35 | GND |
| 5 | Up | GPIO26 | 37 | GND |
| 6 | Down | GPIO21 | 40 | GND |
| Shared ground | GND bus | GND | 39 | All button grounds |

Each button is normally open. One leg goes to the assigned GPIO pin, and the other leg goes to GND. The software uses internal pull-up resistors.

## Step-by-step button build

1. Print the front-panel/button bezel from the production ZIP. The previous four-button bezel should be replaced by a six-button bezel or drilled panel with six 6mm tactile switch positions.
2. Dry-fit six tactile switches in the bezel/front panel and label the positions left-to-right as 1 through 6.
3. Solder or crimp one signal wire to each button.
4. Daisy-chain the other side of all six buttons to a shared black GND wire.
5. Connect Button 1 to Pi GPIO5 / physical pin 29.
6. Connect Button 2 to Pi GPIO6 / physical pin 31.
7. Connect Button 3 to Pi GPIO13 / physical pin 33.
8. Connect Button 4 to Pi GPIO19 / physical pin 35.
9. Connect Button 5 to Pi GPIO26 / physical pin 37.
10. Connect Button 6 to Pi GPIO21 / physical pin 40.
11. Connect the shared ground to Pi physical pin 39.
12. Add heat-shrink and strain relief so the button harness cannot pull on the Pi header.
13. Boot the Pi and install requirements:

```bash
cd pi-companion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

14. Run the six-button GPIO test:

```bash
python3 scripts/test_gpio_buttons.py
```

15. Press each button from left to right and verify the output matches buttons 1 through 6.
16. Hold Button 3 for 3 seconds and verify a `shutdown` hold event is printed.
17. Run the companion:

```bash
python -m koalablue.app --serial /dev/ttyACM0
```

18. Verify events are logged in:

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
- [ ] All six front buttons generate GPIO button events.
- [ ] Button 3 short press emits `select`.
- [ ] Button 3 hold emits `shutdown`.
- [ ] Shared GND bus is secure.
- [ ] Button harness has strain relief.
- [ ] Case closes without pinching wires.
- [ ] 5V rail remains within 5.05 V to 5.15 V under load.
