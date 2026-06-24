# Mined Heltec V2 Features

This active KoalaByte Blue V2 Heltec Edition branch mined selected additive files from the `Backup_heltec` branch.

The goal was not a blind merge. `Backup_heltec` diverged heavily from `main`, so only useful, non-conflicting pieces were copied forward and wired into the current Heltec T114-primary architecture.

## Added safely

First pass:

- `pi-companion/koalablue/t114_bluez.py` — checks whether the Heltec T114 is exposed as a USB Bluetooth HCI controller and wraps safe BlueZ actions.
- `pi-companion/koalablue/location_password_gate.py` — local protected-actions password gate for sensitive location/GNSS actions.
- `pi-companion/koalablue/gnss_location.py` — password-gated GNSS/current-fix helper with environment, saved-fix, and Meshtastic info parsing support.
- `pi-companion/koalablue/meshtastic_app.py` — Meshtastic status/nodes/GPS wrapper plus protected listen/send actions.
- `scripts/run_t114_bluez.py` — CLI for the T114 BlueZ/HCI wrapper.
- `scripts/run_meshtastic_app.py` — CLI for the Meshtastic helper.
- `scripts/run_location_password_gate.py` — CLI for setup/status/unlock of protected local actions.
- `pi-companion/requirements-heltec-v2-extra.txt` — optional extra dependencies for Meshtastic/GNSS/T114 workflows.

Second pass:

- `docs/ESP32_TOUCH_MENU_CALIBRATION.md` — ESP32-S3 DualEye touch JSON protocol and calibration notes. This was already present on the active branch and confirmed during the second pass.
- `pi-companion/koalablue/esp32_touch_menu_bridge.py` — Pi-side bridge from ESP32 menu-touch JSON events into the KoalaByte menu state machine. This was already present on the active branch and confirmed during the second pass.
- `scripts/run_esp32_touch_menu_bridge.py` — optional runtime bridge for ESP32-S3 touch events. This was already present on the active branch and confirmed during the second pass.
- `pi-companion/koalablue/killerkoala_face_bridge.py` — optional face-state JSON bridge for ESP32-S3 DualEye and optional Heltec USB display state output.
- `pi-companion/koalablue/killerkoala_voice_face_control.py` — optional voice-command runner that mirrors wake/thinking/action/speaking states to the face bridge.
- `scripts/run_killerkoala_face_demo.py` — optional demo runner for wake/thinking/action/speaking/success face states.

## Wired into the current branch

The mined Heltec/Meshtastic/location features are exposed through the KoalaByte menu under:

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

The face bridge remains optional and is not part of the default boot path. Use it manually with:

```bash
PYTHONPATH=pi-companion python scripts/run_killerkoala_face_demo.py --sequence
```

## Safety and deployment rules

- The Heltec Mesh Node T114 onboard nRF52840 remains the primary BLE board for the Heltec Edition.
- The ESP32-S3 DualEye remains the face/UI/buttons/secondary BLE node.
- Raspberry Pi BlueZ remains secondary/fallback unless the user explicitly flashes an optional T114 HCI profile.
- Meshtastic send requires both `--confirm-send` and the protected-actions password gate.
- Protected GNSS/location helpers do not write coordinates unless the protected-actions gate is unlocked.
- Optional extra dependencies are not forced into the base install; use `pi-companion/requirements-heltec-v2-extra.txt` when enabling those workflows.
- KillerKoala face bridge commands are JSON display-state messages only. They do not run BLE scans, transmit radio packets, or alter the current one-shot install path.

## Useful validation commands

```bash
python scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python scripts/check_menu_actions.py
PYTHONPATH=pi-companion python scripts/check_esp32_touch_menu.py
PYTHONPATH=pi-companion python scripts/run_location_password_gate.py status
PYTHONPATH=pi-companion python scripts/run_t114_bluez.py controller-check
PYTHONPATH=pi-companion python scripts/run_meshtastic_app.py status
PYTHONPATH=pi-companion python scripts/run_killerkoala_face_demo.py --state wake --message "killerkoala online"
```

The T114 BlueZ and Meshtastic commands are allowed to report missing hardware or missing CLI tools. That is not a repo failure; it means the optional hardware/tooling path is not active on that Pi yet.
