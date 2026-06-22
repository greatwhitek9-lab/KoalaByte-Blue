# Canonical Heltec Edition Branch

The canonical KoalaByte Blue Heltec Edition branch is:

```text
koalabyte_blue_v2_heltec_edition
```

The shorter `heltec` branch was previously used as a compatibility alias. It is no longer required for the installer or normal development once the repo has this document and the updated `scripts/flash_all_components.sh`.

## Current policy

- New Heltec Edition development targets `koalabyte_blue_v2_heltec_edition`.
- Installer scripts should checkout `koalabyte_blue_v2_heltec_edition` through `KOALABYTE_HELTEC_BRANCH`, which defaults to the canonical branch.
- The `heltec` branch may be deleted after confirming it is identical to the canonical branch and no GitHub settings, rules, or open PRs target it.
- The Heltec Edition hardware profile remains Raspberry Pi + ESP32-S3 DualEye + Heltec T114.

## Optional compatibility

If a local workflow still expects a shorter branch name, recreate or sync an alias locally only:

```bash
git fetch origin koalabyte_blue_v2_heltec_edition
git branch -f heltec origin/koalabyte_blue_v2_heltec_edition
```

Do not use `heltec` as the production source of truth.

## Delete command for maintainers

After confirming the remote alias is no longer needed:

```bash
git push origin --delete heltec
```
