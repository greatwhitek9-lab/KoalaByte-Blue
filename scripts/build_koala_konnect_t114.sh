#!/usr/bin/env bash
set -euo pipefail

# Optional Koala Konnect profile for the canonical Heltec Edition branch.
# This builds the Heltec T114 nRF52840 USB HCI controller profile.
# It does not flash the board; use scripts/flash_koala_konnect_t114.sh or
# scripts/flash_all_components.sh --nrf-konnect for flashing.

export KOALA_KONNECT_MODE_NAME="t114_koala_konnect"
export KOALA_KONNECT_HOST_EXPECTATION="USB Bluetooth HCI adapter mode for supported lab hosts with compatible Bluetooth HCI support"

T114_BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840}" bash scripts/build_nrf52840_t114_hci_usb.sh
