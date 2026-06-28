# ESP32-S3 DualEye Touch Menu Calibration

The exact board shown is treated as the Waveshare ESP32-S3 DualEye/Touch 1.28 class board. KoalaByte now includes a direct ESP32 firmware touch backend for the CST816x capacitive touch-controller family used by the Waveshare round touch LCD boards.

## Current firmware behavior

The ESP32-S3 DualEye firmware now does three things:

- Initializes the Waveshare CST816x-style I2C touch controller during ESP32 setup.
- Polls the touch controller inside the ESP32 main loop.
- Emits `menu_touch` JSON events to the Raspberry Pi so the wrapped KoalaByte menu can navigate/select without terminal input.

The previous serial-calibrated test path still exists. That means bench commands such as `simulate_touch`, `raw_touch`, `touch_status`, `touch_calibration`, and `menu_frame` still work for testing and calibration.

## Default Waveshare touch settings

```text
TOUCH_MENU_BACKEND     waveshare_cst816x_i2c
TOUCH_MENU_CONTROLLER  CST816x
TOUCH_MENU_I2C_ADDR    0x15
TOUCH_MENU_I2C_SDA_PIN 6
TOUCH_MENU_I2C_SCL_PIN 7
TOUCH_MENU_INT_PIN     5
TOUCH_MENU_RST_PIN     13
TOUCH_MENU_SCREEN_W    240
TOUCH_MENU_SCREEN_H    240
```

These are firmware defaults and can still be overridden in PlatformIO build flags if a specific board revision uses different pins.

## ESP32 commands

Menu geometry:

```json
{"type":"menu_frame","screen_w":240,"screen_h":240,"row_height":40,"visible_rows":6}
```

Calibration:

```json
{"type":"touch_calibration","raw_min_x":0,"raw_max_x":239,"raw_min_y":0,"raw_max_y":239,"screen_w":240,"screen_h":240,"row_height":40,"visible_rows":6,"invert_x":false,"invert_y":false,"swap_xy":false}
```

Status:

```json
{"type":"touch_status"}
```

Touch sample or test event:

```json
{"type":"simulate_touch","event":"tap","x":120,"y":80}
```

## Pi bridge

```bash
python3 scripts/run_esp32_touch_menu_bridge.py --port /dev/koalabyte-esp32-eyes --calibrate
```

The bridge logs interpreted menu events to:

```text
logs/esp32_touch_menu_events.jsonl
```

## Behavior

- Tap/up selects the row under the touch coordinate.
- Move/drag scrolls through menu rows.
- Long press selects/activates the highlighted item.
- Buttons remain active as fallback input.

## If touch is reversed or rotated

Send a calibration JSON with one or more of these changed:

```json
{"type":"touch_calibration","invert_x":true,"invert_y":false,"swap_xy":false}
```

Use `touch_status` afterward to confirm the active values.
