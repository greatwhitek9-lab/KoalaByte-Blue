# Mined Heltec v2 features

This canonical Heltec Edition branch mined selected additive files from the older `koalabyte-blue-v2-heltec-edition` branch.

The goal was not a blind merge. The older branch diverged heavily, so only useful, non-conflicting pieces were copied forward.

## Added safely

- `pi-companion/koalablue/t114_bluez.py` — checks whether the Heltec T114 is exposed as a USB Bluetooth HCI controller and wraps safe BlueZ actions.
- `pi-companion/koalablue/location_password_gate.py` — local protected-actions password gate for sensitive location/GNSS actions.
- `pi-companion/koalablue/gnss_location.py` — password-gated GNSS/current-fix helper with environment, saved-fix, and Meshtastic info parsing support.
- `pi-companion/koalablue/meshtastic_app.py` — Meshtastic status/nodes/GPS wrapper plus protected listen/send actions.
- `scripts/run_t114_bluez.py` — CLI for the T114 BlueZ/HCI wrapper.
- `scripts/run_meshtastic_app.py` — CLI for the Meshtastic helper.
- `scripts/run_location_password_gate.py` — CLI for setup/status/unlock of protected local actions.
- `scripts/confirm_t114_board_target.sh` — resolves an available T114 Zephyr board target or reports a safe CI smoke-test fallback.
- `scripts/configure_t114_2g4_antenna.sh` — documents/configures the physical 2.4 GHz antenna connector path and optional validated RF-switch overlay.
- `scripts/build_nrf52840_t114_hci_usb.sh` — builds Zephyr HCI USB firmware for the T114 profile.
- `scripts/flash_nrf52840_t114_hci_usb.sh` — flashes the HCI USB firmware by `west` or UF2 path.
- `pi-companion/requirements-heltec-v2-extra.txt` — optional extra dependencies for Meshtastic/GNSS/T114 workflows.

## Integrated into optional Koala Konnect

The optional Koala Konnect action is now wired through:

```bash
bash scripts/flash_all_components.sh --nrf-konnect
```

On this Heltec Edition branch, `--nrf-konnect` builds and flashes the Heltec T114 USB HCI profile with:

```bash
T114_BOARD=${T114_BOARD:-heltec_t114_v2/nrf52840} bash scripts/build_nrf52840_t114_hci_usb.sh
T114_FLASH_METHOD=${T114_FLASH_METHOD:-west} bash scripts/flash_nrf52840_t114_hci_usb.sh
```

This is intentionally optional. It is not part of `--all` or `--install-firmware` because flashing the T114 USB HCI profile replaces the normal Heltec mouth/GNSS/BLE-primary firmware until the normal profile is flashed back.

## Intentionally not blindly merged

- Older config files and menu definitions were not copied over because the canonical branch already has newer stable hardware hardening, CAN setup, BLE service, and touch-menu integration.
- Legacy branch-specific or stale workflow files were not copied until they can be reviewed against the current CI layout.
- Any Meshtastic send action requires explicit `--confirm-send` and the protected-actions password gate.

## Recommended validation

```bash
python scripts/check_repo_readiness.py
python scripts/run_location_password_gate.py status
python scripts/run_t114_bluez.py controller-check
python scripts/run_meshtastic_app.py status
```

For optional Koala Konnect / T114 HCI USB build validation:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect --build-only
```
