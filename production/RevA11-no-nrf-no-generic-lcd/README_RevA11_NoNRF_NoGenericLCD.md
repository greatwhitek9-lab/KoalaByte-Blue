# KoalaByte Blue RevA11 Production BOM
## No nRF52840 / No Generic LCD Build

This production BOM defines the physical KoalaByte Blue RevA11 build after removing:

- Nordic nRF52840 DK / PCA10056
- Nordic nRF52840 Dongle / PCA10059
- Generic HDMI LCD / generic touchscreen LCD

## Required Architecture

- Main computer: Raspberry Pi 3B+
- BLE interface: Raspberry Pi 3B+ onboard Bluetooth/BLE
- Display/face: ESP32-S3 DualEye-LCD-1.28 only
- Controls: Six front-panel physical buttons
- Touch input: optional USB HID touch input layer only; no generic LCD is included
- Case: printed koala enclosure with no generic LCD opening

## Included Files

- BOM_RevA11_NoNRF_NoGenericLCD.xlsx
- BOM_RevA11_NoNRF_NoGenericLCD.csv
- README_RevA11_NoNRF_NoGenericLCD.md

## Feature Mapping

- eucalyptus: always-on passive BLE scanner/logger
- Koala Kapture: capture/archive BLE advertisement metadata
- Koala Kry: replay captured BLE metadata into UI/report/XP flows
- Ear Tag: named lab beacon workflow
- Urban Poaching: authorized BLE RSSI lab game
- KillerKoala: AI companion and leveling system

## Physical Build Notes

The RevA11 production case should:

- Remove the generic LCD window
- Keep the ESP32-S3 DualEye face/display mount
- Keep six-button front bezel
- Keep speaker grill
- Keep venting
- Keep access to USB, power switch, and charging/service ports
- Use top antenna cutout plugs unless optional antenna hardware is installed later

## Safety Boundary

This hardware BOM is for authorized Bluetooth research, local metadata capture/replay,
UI testing, reports, and companion-device behavior. It does not include RF noise
generation or wireless interference hardware.
