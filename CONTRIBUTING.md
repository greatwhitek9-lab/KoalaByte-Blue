# Contributing to KoalaByte Blue

KoalaByte Blue coordinates Raspberry Pi services, ESP32-S3 firmware, Heltec T114 firmware, displays, audio, BLE/Wi-Fi links, and physical controls. Keep changes narrow enough to validate and review without obscuring hardware regressions.

## Change discipline

- Create a focused branch and keep unrelated cleanup out of functional changes.
- Preserve the canonical deployment path: `install.sh` invokes `one-shot-install.sh`.
- Do not replace known-working device behavior without documenting the previous behavior, the intended change, and the recovery path.
- Keep hardware-specific changes isolated under the relevant firmware or Pi component.
- Update documentation whenever commands, paths, services, pin assignments, protocol fields, or ownership roles change.
- Never commit credentials, private keys, local `.env` files, generated logs, release bundles, SDK worktrees, or build output.

## Repository areas

| Path | Responsibility |
|---|---|
| `firmware/esp32-dualeye/` | Waveshare ESP32-S3 DualEye firmware and generated voice/display assets |
| `firmware/heltec-mouth/` | Heltec T114 mouth, Koalagotchi, BLE, and status firmware |
| `pi-companion/` | Raspberry Pi runtimes and supporting Python components |
| `scripts/` | Installation, validation, diagnostics, release, and hardware utilities |
| `systemd/` | Service definitions and templates |
| `udev/` | Stable device naming rules |
| `version/` | Cross-device protocol/version contracts |
| `docs/` | Hardware and operating documentation |

See [docs/README.md](docs/README.md) for the documentation index.

## Validation

Run the checks relevant to the files changed. The source-level baseline is:

```bash
python3 scripts/check_whole_system_deployment.py --source-only
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
PYTHONPATH=pi-companion python3 scripts/check_music_player.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_ai.py
PYTHONPATH=pi-companion python3 scripts/check_ble_role_failover.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_error_sequence.py
bash scripts/check_deployability.sh
bash one-shot-install.sh --check-only
```

When the embedded toolchains are available, compile each affected firmware target:

```bash
pio run -d firmware/esp32-dualeye
pio run -d firmware/heltec-mouth
```

Hardware-affecting changes also require bench verification on the actual target device. Record the board, port, build environment, observed boot/status output, and any manual recovery action in the pull request.

## Pull requests

Describe:

1. What changed and why.
2. Which devices or services are affected.
3. Which checks were run and their results.
4. What was not tested.
5. Any flashing, migration, rollback, or recovery steps.

Prefer a draft pull request until source checks pass and any required hardware verification is complete.
