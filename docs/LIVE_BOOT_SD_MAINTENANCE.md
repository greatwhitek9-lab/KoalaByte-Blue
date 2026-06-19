# KoalaByte Blue Live Boot SD Maintenance

KoalaByte Blue runs from the Raspberry Pi boot microSD card. That card cannot be safely formatted while the Pi is actively booted from it.

This tool exists for the live boot card, but it does **maintenance**, not self-formatting:

- Identifies the current root/boot source.
- Shows disk size and used/free space.
- Explains that self-formatting is blocked.
- Can clear KoalaByte-generated logs/cache data after confirmation.
- Can optionally clear `/blecaptures` after confirmation.

For a true format or reimage of the boot card, remove the card and use Raspberry Pi Imager or another computer.

## Show boot-card status

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_sd_maintenance.py status
```

JSON output:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_sd_maintenance.py status --json
```

## Preview a KoalaByte data reset

This does not remove anything:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_sd_maintenance.py reset-data --dry-run
```

Include capture storage in the preview:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_sd_maintenance.py reset-data --dry-run --include-captures
```

## Reset KoalaByte-generated live-card data

This removes KoalaByte logs/caches but does not remove Raspberry Pi OS, user accounts, networking, packages, firmware source, or the repo itself.

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_sd_maintenance.py reset-data \
  --confirm RESET-KOALABYTE-LIVE-SD
```

To also remove `/blecaptures`:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_sd_maintenance.py reset-data \
  --include-captures \
  --confirm RESET-KOALABYTE-LIVE-SD
```

## What this is not

This is not a live-card format command. A live self-format would destroy the mounted root filesystem while Linux is using it. KoalaByte Blue blocks that behavior by design.

Use the separate SD Card Formatter only for a secondary/removable card in a USB reader:

```bash
PYTHONPATH=pi-companion python3 scripts/run_sd_card_formatter.py list
```
