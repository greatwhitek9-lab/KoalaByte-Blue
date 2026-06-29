# ESP32-S3 DualEye Touch Menu Calibration

Board target: **Waveshare ESP32-S3-DualEye-Touch-LCD-1.28**.

KoalaByte uses the Waveshare pinout from the official board definition and wiki. The board has two 1.28 inch 240 × 240 LCDs, I2C touch with interrupt, 16 MB flash, 8 MB PSRAM, Type-C USB, ES8311 audio codec, ES7210 microphone path, onboard ceramic antenna, and an optional IPEX1 antenna path that requires moving/resoldering the antenna selector resistor.

## Current firmware behavior

The ESP32-S3 DualEye firmware does three things:

- Initializes the Waveshare CST816D/CST816x I2C touch controller during ESP32 setup.
- Polls the touch controller inside the ESP32 main loop.
- Emits `menu_touch` JSON events to the Raspberry Pi so the wrapped KoalaByte menu can navigate/select without terminal input.

The serial-calibrated test path still exists. Commands such as `simulate_touch`, `raw_touch`, `touch_status`, `touch_calibration`, and `menu_frame` still work for testing and calibration.

## Waveshare display settings

```text
DISPLAY_DRIVER         GC9A01
DISPLAY_WIDTH          240
DISPLAY_HEIGHT         240
DISPLAY_SPI_SCLK_PIN   GPIO4
DISPLAY_SPI_MOSI_PIN   GPIO2
DISPLAY_SPI_CS_PIN     GPIO5
DISPLAY_SPI_DC_PIN     GPIO47
DISPLAY_SPI_RESET_PIN  GPIO38
DISPLAY_BACKLIGHT_PIN  GPIO42
DISPLAY_MIRROR_X       true
DISPLAY_MIRROR_Y       false
DISPLAY_SWAP_XY        false
DISPLAY_SPI_SCLK_HZ    40000000
```

The PlatformIO environment configures TFT_eSPI with `GC9A01_DRIVER`, 240 × 240 resolution, the Waveshare SPI pins above, 16 MB flash, OPI PSRAM, and USB CDC on boot.

## Default Waveshare touch settings

```text
TOUCH_MENU_BACKEND     waveshare_cst816d_i2c
TOUCH_MENU_CONTROLLER  CST816D
TOUCH_MENU_I2C_ADDR    0x15
TOUCH_MENU_I2C_SDA_PIN GPIO11
TOUCH_MENU_I2C_SCL_PIN GPIO7
TOUCH_MENU_INT_PIN     GPIO12
TOUCH_MENU_RST_PIN     GPIO6
TOUCH_MENU_SCREEN_W    240
TOUCH_MENU_SCREEN_H    240
TOUCH_MENU_POLL_MS     10
```

## Waveshare audio pin reference

```text
AUDIO_I2S_MCLK_PIN     GPIO16
AUDIO_I2S_WS_PIN       GPIO45
AUDIO_I2S_BCLK_PIN     GPIO9
AUDIO_I2S_DIN_PIN      GPIO10
AUDIO_I2S_DOUT_PIN     GPIO8
AUDIO_CODEC_PA_PIN     GPIO46
AUDIO_CODEC_I2C_SDA    GPIO15
AUDIO_CODEC_I2C_SCL    GPIO14
```

KoalaByte uses these pins as firmware constants so the board reports the right audio and mic wiring. The Pi remains the main companion/voice brain.

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
