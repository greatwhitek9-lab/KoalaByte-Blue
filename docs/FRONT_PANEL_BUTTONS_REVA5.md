# RevA6 Front Panel Button Mapping

## Does the Nordic nRF52840 Dongle have buttons?

Yes, but only one tiny onboard user-programmable button. Nordic documents the nRF52840 Dongle as having a user-programmable RGB LED, green LED, one user-programmable button, and 15 GPIOs available on castellated edge pads.

For KoalaByte Blue, that onboard button is not enough for a case-mounted user interface. RevA6 uses six external front-panel buttons wired to the Raspberry Pi 3B+ GPIO header.

## Exact button part in BOM

- **Adafruit Tactile Button switch (6mm) x 20 pack**
- **Product ID: 367**
- Six buttons are used, numbered **1 through 6 from left to right**.
- The pack provides extras for spares and mistakes.

## Six-button map, left to right

| Button # | Front-panel label | Action | Raspberry Pi BCM GPIO | Physical pin | Other side of button |
|---:|---|---|---:|---:|---|
| 1 | Main Menu | `main_menu` | GPIO5 | Pin 29 | GND |
| 2 | Left / Back | `move_left` / `back` | GPIO6 | Pin 31 | GND |
| 3 | Enter / Select | `select`; hold 3 seconds for `shutdown` | GPIO13 | Pin 33 | GND |
| 4 | Right / Forward | `move_right` / `forward` | GPIO19 | Pin 35 | GND |
| 5 | Up | `up` | GPIO26 | Pin 37 | GND |
| 6 | Down | `down` | GPIO21 | Pin 40 | GND |

Use physical pin 39 as the preferred shared ground bus.

## Wiring rule

Each normally-open button has two sides:

```text
GPIO pin -> button -> GND
```

No external pull-up resistor is required. The Raspberry Pi internal pull-up is enabled by `gpiozero` in software.

## Shutdown hold behavior

Button 3 has two behaviors:

- Normal press: `select`
- Hold for 3 seconds: `shutdown`

The GPIO test script only prints the shutdown event. The production companion should confirm shutdown in the UI before invoking a real system shutdown.
