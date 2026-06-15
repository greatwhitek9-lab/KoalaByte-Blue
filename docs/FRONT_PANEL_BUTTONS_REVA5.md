# RevA5 Front Panel Buttons

## Does the Nordic nRF52840 Dongle have buttons?

Yes, but only one tiny onboard user-programmable button. Nordic documents the nRF52840 Dongle as having a user-programmable RGB LED, green LED, one user-programmable button, and 15 GPIOs available on castellated edge pads.

For KoalaByte Blue, that onboard button is not enough for a case-mounted user interface. RevA5 therefore adds four external front-panel buttons wired to the Raspberry Pi 3B+ GPIO header.

## Exact button part added to BOM

- **Adafruit Tactile Button switch (6mm) x 20 pack**
- **Product ID: 367**
- Four buttons are used: Back, Select, Next, Menu.
- The pack provides extras for spares and mistakes.

## Button map

| Function | Raspberry Pi BCM GPIO | Physical pin | Other side of button |
|---|---:|---:|---|
| Back | GPIO5 | Pin 29 | GND |
| Select | GPIO6 | Pin 31 | GND |
| Next | GPIO13 | Pin 33 | GND |
| Menu | GPIO19 | Pin 35 | GND |

Use physical pin 39 as the preferred ground bus.

## Wiring rule

Each normally-open button has two sides:

```text
GPIO pin -> button -> GND
```

No external pull-up resistor is required. The Raspberry Pi internal pull-up is enabled by `gpiozero` in software.
