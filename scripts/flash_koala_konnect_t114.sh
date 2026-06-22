#!/usr/bin/env bash
set -euo pipefail

# Optional Koala Konnect profile for the canonical Heltec Edition branch.
# This flashes the Heltec T114 nRF52840 USB HCI controller profile.
# Flashing this profile replaces the normal Heltec mouth/GNSS/BLE-primary firmware
# until scripts/flash_heltec_mouth.sh is used to flash the normal profile back.

export KOALA_KONNECT_MODE_NAME="t114_koala_konnect"
export KOALA_KONNECT_HOST_EXPECTATION="After replugging, supported lab hosts can use the Heltec board as a USB Bluetooth HCI adapter when host driver support is available."

T114_FLASH_METHOD="${T114_FLASH_METHOD:-west}" bash scripts/flash_nrf52840_t114_hci_usb.sh
