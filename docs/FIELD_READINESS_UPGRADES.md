# KoalaByte Blue Field Readiness Upgrades

This document summarizes the field-use additions on the default `koalabyte-blue-v2-heltec-edition` branch.

## 1. KoalaByte Doctor

Run a quick local status sweep:

```bash
bash scripts/koalabyte_doctor.sh --quick
```

Run a fuller sweep:

```bash
bash scripts/koalabyte_doctor.sh
```

Output:

```text
logs/doctor/koalabyte_doctor_status.json
```

## 2. Stable device names

Install stable serial aliases:

```bash
bash scripts/install_koalabyte_udev_rules.sh
```

Check only:

```bash
bash scripts/install_koalabyte_udev_rules.sh --check-only
```

Expected aliases include:

```text
/dev/koalabyte-esp32-dualeye
/dev/koalabyte-heltec
/dev/koalabyte-nrf52840
```

## 3. Boot services

Templates live in `systemd/`:

```text
koalabyte-menu.service
koalabyte-menu-sync.service
koalabyte-doctor.service
```

Install them with:

```bash
bash scripts/install_koalabyte_boot_services.sh
```

## 4. Safe mode

Safe mode disables strict optional services and opens a recovery-friendly state:

```bash
bash scripts/koalabyte_safe_mode.sh
bash scripts/koalabyte_safe_mode.sh --terminal
bash scripts/koalabyte_safe_mode.sh --doctor
```

## 5. Log export

Bundle the important logs for debugging:

```bash
bash scripts/export_koalabyte_logs.sh
```

Output goes to `exports/`.

## 6. One-shot dry-run target

The preferred goal is:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

The current supporting checks are already committed as standalone scripts. If the one-shot installer cannot be edited by the repo write guard in one pass, run these directly:

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_menu_display_sync.py
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
PYTHONPATH=pi-companion python3 scripts/check_koalabyte_version_handshake.py
bash scripts/koalabyte_doctor.sh --quick
```

## 7. Version handshake

The version manifest is:

```text
version/koalabyte_protocol.json
```

Check Pi/ESP32/Heltec protocol readiness:

```bash
PYTHONPATH=pi-companion python3 scripts/check_koalabyte_version_handshake.py
```

## 8. Local status dashboard

Run a local dashboard:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koalabyte_status_server.py --host 0.0.0.0 --port 8080
```

JSON-only check:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koalabyte_status_server.py --json
```

## 9. Log rotation

Config template:

```text
logrotate/koalabyte-blue
```

Install manually on the Pi:

```bash
sudo install -m 0644 logrotate/koalabyte-blue /etc/logrotate.d/koalabyte-blue
```

## 10. Release package

Build locally:

```bash
bash scripts/build_koalabyte_release_package.sh
```

Or run the GitHub workflow:

```text
.github/workflows/release-package.yml
```
