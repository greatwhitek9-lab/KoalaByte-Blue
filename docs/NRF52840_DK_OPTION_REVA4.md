# RevA4 Hardware Change: Optional nRF52840 DK Development Board

KoalaByte Blue now supports a two-board Nordic workflow:

```text
Production compact BLE board: Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
Optional development/debug board: Nordic nRF52840 DK / PCA10056
```

## Why this change

The nRF52840 Dongle stays in the final physical KoalaByte Blue stack because it is compact, USB powered, and easy to mount. The nRF52840 DK is added as an optional development tool because it is easier for firmware development, debugging, current measurement, and recovery.

## Hardware roles

| Board | Model | Use in project | Final device? |
|---|---|---|---|
| nRF52840 Dongle | PCA10059 / NRF52840-DONGLE | Compact USB BLE board used in the production-style KoalaByte Blue build | Yes |
| nRF52840 DK | PCA10056 | Optional firmware-development, validation, and debug board | No, unless building a bench-only dev rig |

## Physical build guidance

Keep the Dongle in the 3D printed / stacked device. Keep the DK outside the final enclosure as a bench development and validation board.

Recommended workflow:

1. Develop BLE firmware and lab peripheral behavior on the nRF52840 DK.
2. Validate advertisement names, GATT service structure, serial/logging output, and safe lab behavior.
3. Keep the Dongle in the final KoalaByte Blue stack for compact scanning/sniffing/support workflows.
4. Do not enlarge the production case to fit the DK unless you specifically want a bench-only enclosure.

## BOM update

Add this optional line to the production BOM:

```csv
Optional development board,Nordic nRF52840 DK,PCA10056,0-1,Nordic/DigiKey/Mouser,Firmware development and debugging only; not required in final compact build
```

## Safety boundary

The DK firmware added in this repo is a safe lab peripheral demo. It advertises as a clearly labeled KoalaByte lab device and exposes a read-only GATT status characteristic. It does not impersonate third-party devices and does not perform unauthorized connection, pairing, injection, disruption, tracking, or bypass behavior.
