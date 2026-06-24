# Heltec Branch Mining Findings

This note records the Heltec branch/history mining pass for the active `koalabyte_blue_v2_heltec_edition` line.

## Source status

A pushed GitHub ref named `backup_Heltec` was not reachable from the installed repository connection. The following refs were also checked and did not resolve:

- `backup_Heltec`
- `backup-Heltec`
- `backup_heltec`
- `heltec_backup`
- `backup/Heltec`
- `backup/heltec`

Because the named backup ref was unavailable, the mining pass used the reachable Heltec commit trail and current Heltec files in `main`.

## Mined findings applied to the active branch

The useful Heltec findings are now expected to remain true for the active branch:

1. The **Heltec Mesh Node T114 onboard nRF52840** is the primary BLE board and canonical passive BLE source.
2. The one-shot installer must set or honor `KOALABYTE_PRIMARY_BLE_PORT`, `KOALABYTE_HELTEC_USB_PORT`, and the legacy-compatible `KOALABYTE_NRF_BLE_PORT` alias.
3. Legacy external nRF52840 dongle firmware targets must remain explicit opt-in targets only.
4. The one-shot installer must run Heltec T114 dependency setup before the BLE node-manager path.
5. The one-shot installer must validate all enabled menu items with `scripts/check_menu_actions.py` without executing those menu actions.
6. AntEater must be part of the one-shot readiness path, but the flasher must not start a live BLE scan.
7. The Raspberry Pi install path must run the Heltec dependency helper and leave legacy dongle cache preparation opt-in.
8. Stable device aliases should prefer `/dev/koalabyte-heltec` for the Heltec primary board and `/dev/koalabyte-esp32-eyes` for the ESP32-S3 DualEye board.
9. CI/readiness must catch stale architecture text that makes the external nRF52840 USB Dongle look like the default primary BLE board.
10. Deployability checks should validate shell syntax, required files, menu routing, and one-shot installer hooks.

## Current implementation map

| Finding | Active implementation |
|---|---|
| Heltec T114 onboard nRF52840 is primary | `docs/MAIN_BLE_NODE_ROLES.md`, `pi-companion/koalablue/ble_event_log.py`, `pi-companion/koalablue/ble_node_manager.py` |
| Primary Heltec serial variables | `scripts/discover_koalabyte_ports.py`, `scripts/run_ble_node_manager.py`, `scripts/flash_all_components.sh` |
| Stable Heltec udev alias | `scripts/install_koalabyte_udev_rules.sh` |
| One-shot Heltec dependency setup | `scripts/setup_heltec_t114_tools.sh`, `scripts/install_pi.sh`, `scripts/flash_all_components.sh` |
| Full menu readiness | `pi-companion/koalablue/menu_catalog.py`, `scripts/check_menu_actions.py`, `scripts/flash_all_components.sh` |
| AntEater readiness | `pi-companion/koalablue/anteater.py`, `scripts/run_anteater.py`, `docs/ANTEATER_BLE_CARD_SKIMMER_DETECTOR.md`, `scripts/flash_all_components.sh` |
| Legacy dongle opt-in only | `scripts/build_firmware_all.sh`, `scripts/flash_all_components.sh`, legacy firmware READMEs |
| Deployability gate | `scripts/check_repo_readiness.py` |

## Active branch rule

If a future branch or local backup named `backup_Heltec` becomes available, compare it against `main` and only import changes that preserve the current architecture:

```text
Heltec Mesh Node T114 onboard nRF52840 -> primary BLE board
ESP32-S3 DualEye -> UI/eyes/buttons/secondary BLE node
Raspberry Pi BlueZ -> secondary/fallback host node
Legacy external nRF52840 Dongle -> opt-in compatibility only
```

Any mined change that violates that rule should stay out of the active Heltec Edition branch.
