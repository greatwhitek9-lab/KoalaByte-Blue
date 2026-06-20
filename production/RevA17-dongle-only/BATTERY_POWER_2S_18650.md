# KoalaByte Blue RevA17 Battery Power Guide

This file updates the RevA17 dongle-only production package to use a **2x18650 battery-powered 2S Li-ion pack** as the primary power source.

## Battery topology

```text
2x 18650 Li-ion cells in series
  -> 2S Li-ion BMS / protection board
  -> inline 5 A fuse
  -> main power switch
  -> 5 V buck converter set to 5.1 V
  -> +5 V / GND distribution rails
  -> Raspberry Pi 3B+ / ESP32-S3 DualEye / fan / speaker amp / accessories
```

Nominal battery voltage:

```text
2S pack nominal: 7.4 V
2S pack fully charged: 8.4 V
```

The Raspberry Pi and ESP32 are still powered from a regulated 5 V rail. The raw 2S battery voltage must never be connected directly to the Pi, ESP32-S3, nRF52840 dongle, USB-CAN adapter, fan, speaker amp, or button wiring.

## Required battery power parts

| Item | Qty | Requirement |
|---|---:|---|
| Matched protected 18650 Li-ion cells | 2 | Same brand/capacity/age; inspect wraps before use. |
| 2x18650 holder | 1 | Use a series holder or holder integrated with a real 2S BMS. |
| 2S Li-ion BMS / protection board | 1 | Must support pack charge/discharge current. |
| Inline ATC/ATO fuse holder | 1 | 18-20 AWG leads preferred. |
| 5 A blade fuse | 1 | Start with 5 A for bring-up. |
| Main power switch | 1 | Rated for DC current draw. |
| 5 V buck converter | 1 | 5 V 3 A minimum; 5 V 5 A preferred. Set to 5.1 V before connecting electronics. |
| +5 V / GND distribution rails | 1 pair | WAGO lever connectors or screw-terminal rail; do not use a breadboard rail for main power. |
| Optional 1000 uF capacitor | 1 | Across the regulated 5 V rail only; stripe/negative to GND. Use 10 V minimum, 16 V preferred. |

## BMS wiring

```text
Cell 1 negative  -> BMS B-
Cell 1 positive  -> Cell 2 negative series midpoint
Series midpoint  -> BMS B1 / BM
Cell 2 positive  -> BMS B+
BMS P+           -> fuse input
Fuse output      -> main switch input
Main switch out  -> buck VIN+
BMS P-           -> buck VIN-
Buck 5V+         -> +5 V rail
Buck GND         -> GND rail
```

## Device power wiring

| Device | Power connection |
|---|---|
| Raspberry Pi 3B+ | Prefer a short low-resistance micro-USB pigtail from the 5.1 V rail for the first build. |
| ESP32-S3 DualEye | 5 V and GND from rails; USB/UART data to Pi as required. |
| nRF52840 USB Dongle | Plugs into Raspberry Pi USB; no separate battery wiring. |
| Optional InnoMaker USB-CAN | Plugs into Raspberry Pi USB; no direct battery wiring. |
| 5 V fan | Red to +5 V rail, black to GND rail. |
| Speaker amp | 5 V/GND rail if using a powered amp module. |
| Six front buttons | Signal-only wiring to GPIO and GND. Do not connect buttons to battery positive or 5 V. |

## USB-C PD trigger board rule

The Seloky USB-C PD/QC 12 V trigger board is no longer the primary production power path for the battery build.

It may be kept only as an **optional external bench/service input path** feeding the buck converter when the battery path is disconnected. It is not a Li-ion charger and it must not be tied directly in parallel with the 2S battery output.

Do not combine USB-C PD output and battery output unless a proper power-path controller, ideal-diode OR-ing module, or charger/load-sharing design is added and tested.

## Bring-up checklist

1. Confirm both 18650 cells are matched and undamaged.
2. Confirm holder polarity and BMS B-, B1/BM, B+ wiring before installing electronics.
3. Install 5 A fuse close to BMS P+.
4. Connect BMS P+ through fuse and switch to buck VIN+.
5. Connect BMS P- to buck VIN-.
6. Power the pack with electronics disconnected.
7. Adjust buck output to about 5.1 V using a multimeter.
8. Power off and connect +5 V/GND rails.
9. Connect Pi power first and confirm it boots without undervoltage warnings.
10. Connect ESP32-S3, fan, speaker amp, nRF52840 dongle, and optional USB-CAN after 5 V rail stability is confirmed.

## Safety boundary

- Do not charge loose cells inside the device unless the installed BMS/charger path is designed and rated for 2S Li-ion charging.
- Do not use damaged cells or torn cell wraps.
- Do not bypass the BMS or fuse.
- Do not feed raw battery voltage into Raspberry Pi GPIO, ESP32 GPIO, USB devices, or button wiring.
- Do not close the case until polarity, voltage, strain relief, and thermal clearance pass inspection.
