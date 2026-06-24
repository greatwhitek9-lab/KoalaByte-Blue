# Mined Heltec V2 Features

This active KoalaByte Blue V2 Heltec Edition branch mined selected additive files from the `Backup_heltec` branch.

The goal was not a blind merge. `Backup_heltec` diverged heavily from `main`, so only useful, non-conflicting pieces were copied forward and wired into the current Heltec T114-primary architecture.

## Added safely

- `pi-companion/koalablue/t114_bluez.py` — checks whether the Heltec T114 is exposed as a USB Bluetooth HCI controller and wraps safe BlueZ actions.
- `pi-companion/koalablue/location_password_gate.py` — local protected-actions password gate for sensitive location/GNSS actions.
- `pi-companion/koalablue/gnss_location.py` — password-gated GNSS/current-fix helper with environment, saved-fix, and Meshtastic info parsing support.
- `pi-companion/koalablue/meshtastic_app.py` — Meshtastic status/nodes/GPS wrapper plus protected listen/send actions.
- `scripts/run_t114_bluez.py` — CLI for the T114 BlueZ/HCI wrapper.
- `scripts/run_meshtastic_app.py` — CLI for the Meshtastic helper.
- `scripts/run_location_password_gate.py` — CLI for setup/status/unlock of protected local actions.
- `pi-companion/requirements-heltec-v2-extra.txt` — optional extra dependencies for Meshtastic/GNSS/T114 workflows.

## Wired into the current branch

The mined features are exposed through the KoalaByte menu under:

```text
Main Canopy -> Heltec / Mesh
```

Menu items added:

- T114 BlueZ Controller Check
- T114 BlueZ Status
- Meshtastic Status
- Meshtastic Nodes
- Meshtastic GPS Info
- Protected Location Gate Status
- Protected GNSS Current Fix

## Safety and deployment rules

- The Heltec Mesh Node T114 onboard nRF52840 remains the primary BLE board for the Heltec Edition.
- The ESP32-S3 DualEye remains the face/UI/buttons/secondary BLE node.
- Raspberry Pi BlueZ remains secondary/fallback unless the user explicitly flashes an optional T114 HCI profile.
- Meshtastic send requires both `--confirm-send` and the protected-actions password gate.
- Protected GNSS/location helpers do not write coordinates unless the protected-actions gate is unlocked.
- Optional extra dependencies are not forced into the base install; use `pi-companion/requirements-heltec-v2-extra.txt` when enabling those workflows.

## Useful validation commands

```bash
python scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python scripts/check_menu_actions.py
PYTHONPATH=pi-companion python scripts/run_location_password_gate.py status
PYTHONPATH=pi-companion python scripts/run_t114_bluez.py controller-check
PYTHONPATH=pi-companion python scripts/run_meshtastic_app.py status
```

The T114 BlueZ and Meshtastic commands are allowed to report missing hardware or missing CLI tools. That is not a repo failure; it means the optional hardware/tooling path is not active on that Pi yet.
