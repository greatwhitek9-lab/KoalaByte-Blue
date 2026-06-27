# KoalaByte Blue Field Readiness Upgrades

This document summarizes the field-use additions on the default `Main` branch.

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

## 6. One-shot dry run

Run the same readiness gate that CI uses before flashing firmware or installing services:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

## 7. Fresh install bootstrap

From a new Raspberry Pi install, use the default `Main` branch bootstrapper:

```bash
curl -fsSL -o koalabyte-install.sh https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/Main/install.sh
bash koalabyte-install.sh
```
