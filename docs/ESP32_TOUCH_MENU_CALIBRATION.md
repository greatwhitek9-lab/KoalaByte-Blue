# ESP32-S3 DualEye Touch Menu Calibration

The KoalaByte menu state machine already supports touch-style navigation on the Raspberry Pi side. The ESP32-S3 DualEye firmware now includes a calibrated menu-touch JSON protocol so the DualEye board can act as an additional menu input source without replacing the six GPIO buttons.

## Hardware note

The ESP32-S3 DualEye touch controller and pinout are board-revision-specific. Until the exact controller is confirmed, the firmware uses the safe serial-calibrated backend:

- The Pi can send calibration and menu geometry to the ESP32.
- The ESP32 can map touch coordinates into screen/menu rows.
- The ESP32 emits menu_touch JSON events.
- The Pi bridge converts those events into MenuSelectionScreen touch down, move, up, and select actions.

## ESP32 commands

Menu geometry:

```json
{"type":"menu_frame","screen_w":240,"screen_h":240,"row_height":40,"visible_rows":6}
```

Calibration:

```json
{"type":"touch_calibration","raw_min_x":0,"raw_max_x":4095,"raw_min_y":0,"raw_max_y":4095,"screen_w":240,"screen_h":240,"row_height":40,"visible_rows":6,"invert_x":false,"invert_y":false,"swap_xy":false}
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

Once the exact board revision and touch controller are confirmed, a hardware reader can feed the same menu-touch protocol without changing the Pi menu bridge.
