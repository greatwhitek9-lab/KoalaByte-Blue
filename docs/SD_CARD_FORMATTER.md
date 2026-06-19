# KoalaByte Blue SD Card Formatter

The SD Card Formatter is a guarded Pi-side utility for preparing a secondary microSD card attached through a USB card reader.

It is intentionally conservative:

- It lists block devices before doing anything destructive.
- It expects a whole-disk path such as `/dev/sda` or `/dev/mmcblk1`.
- It refuses partition paths such as `/dev/sda1`.
- It refuses the live root / boot device.
- It refuses mounted target partitions unless `--unmount` is supplied.
- It refuses disks that do not look removable unless `--allow-non-removable` is supplied after manual verification.
- It defaults to dry-run planning.
- Actual formatting requires the exact phrase `ERASE-KOALABYTE-SD`.

> **Do not use this to prepare the Pi operating-system boot card while KoalaByte Blue is running from that same card.** For the main Pi boot card, use Raspberry Pi Imager from another computer. This utility is for a second/removable card or a card connected through a reader.

## List detected devices

```bash
PYTHONPATH=pi-companion python3 scripts/run_sd_card_formatter.py list
```

JSON output:

```bash
PYTHONPATH=pi-companion python3 scripts/run_sd_card_formatter.py list --json
```

## Preview the format plan

This does not erase anything:

```bash
PYTHONPATH=pi-companion python3 scripts/run_sd_card_formatter.py plan --device /dev/sda --fs fat32 --label KOALABYTE
```

For exFAT:

```bash
PYTHONPATH=pi-companion python3 scripts/run_sd_card_formatter.py plan --device /dev/sda --fs exfat --label KOALABYTE
```

If a known-good USB SD reader does not report itself as removable, use this only after physically checking the card and device path:

```bash
PYTHONPATH=pi-companion python3 scripts/run_sd_card_formatter.py plan \
  --device /dev/sda \
  --fs fat32 \
  --label KOALABYTE \
  --allow-non-removable
```

## Format after verifying the target

After confirming the target is the removable SD card and not the Pi boot card:

```bash
sudo PYTHONPATH=pi-companion python3 scripts/run_sd_card_formatter.py format \
  --device /dev/sda \
  --fs fat32 \
  --label KOALABYTE \
  --confirm ERASE-KOALABYTE-SD
```

If the removable target has mounted partitions and you have confirmed it is safe to detach them:

```bash
sudo PYTHONPATH=pi-companion python3 scripts/run_sd_card_formatter.py format \
  --device /dev/sda \
  --fs fat32 \
  --label KOALABYTE \
  --unmount \
  --confirm ERASE-KOALABYTE-SD
```

## Recommended first-use workflow

1. Insert the removable SD card into a USB reader.
2. Run the list command.
3. Identify the target by size/model/transport.
4. Run the plan command.
5. Remove and reinsert the card if the wrong device appears.
6. Run the format command only after the device path is confirmed.

## Required host tools

The utility uses common Linux disk tools:

- `lsblk`
- `findmnt`
- `wipefs`
- `parted`
- `partprobe`
- `udevadm`
- `mkfs.vfat` for FAT32
- `mkfs.exfat` for exFAT

On Raspberry Pi OS, install the usual formatter dependencies with:

```bash
sudo apt update
sudo apt install -y dosfstools exfatprogs parted util-linux
```

## Safety boundary

This is a local storage preparation utility. It does not flash firmware, modify Bluetooth behavior, touch CAN tooling, or change the KoalaByte Blue defensive monitors.
