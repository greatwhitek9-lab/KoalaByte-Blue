# Canonical Heltec Edition Branch

The canonical KoalaByte Blue Heltec Edition branch is:

```text
koalabyte_blue_v2_heltec_edition
```

The shorter `heltec` branch is kept as a compatibility alias for the same hardware profile.

## Current policy

- New Heltec Edition development should target `koalabyte_blue_v2_heltec_edition`.
- The `heltec` branch should be kept synchronized to the canonical branch when changes are finalized.
- Both branches are intended to represent the same Raspberry Pi + ESP32-S3 DualEye + Heltec T114 hardware profile.

## Sync command for maintainers

When the canonical branch is stable and should update the alias branch:

```bash
git checkout heltec
git reset --hard koalabyte_blue_v2_heltec_edition
git push --force-with-lease origin heltec
```

Or through GitHub refs, move `heltec` to the current `koalabyte_blue_v2_heltec_edition` commit.
