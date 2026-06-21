# AntEater BLE Card Skimmer Detector

AntEater is a defensive KoalaByte Blue action for spotting BLE advertisement patterns that are often worth checking around payment terminals, fuel pumps, kiosks, and other card-reader environments.

It is a triage tool, not proof that a skimmer exists. AntEater looks at local BLE advertisements only and scores indicators such as suspicious payment-related names, generic BLE serial/UART module names, generic UART service UUIDs, strong nearby unnamed devices, and manufacturer data with little readable identity.

## Safety rules

AntEater is advertisement-only. It does not pair, connect, write, replay, spoof, jam, disrupt, or interfere with nearby devices. Use it only on systems you own, manage, or have authorization to inspect.

Raw BLE addresses are redacted by default. Use `--raw-addresses` only when you have written authorization and need raw identifiers in the local report.

## Run from the Pi

```bash
cd ~/KoalaByte-Blue
PYTHONPATH=pi-companion python3 scripts/run_anteater.py scan --scan-seconds 20
```

Show latest status:

```bash
PYTHONPATH=pi-companion python3 scripts/run_anteater.py status
```

Analyze an existing JSON or JSONL BLE observation file instead of scanning live:

```bash
PYTHONPATH=pi-companion python3 scripts/run_anteater.py analyze --input-json logs/example_ble_observations.jsonl
```

Reports are written to `logs/anteater/` as JSON and Markdown. The latest status is written to `logs/anteater/anteater_status.json`.

## Menu action

Open the KoalaByte Blue menu and select **AntEater** under Bluetooth Tools.

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

## Reading results

Risk levels are based on indicator score:

- `low`: background BLE advertisement with no strong skimmer pattern.
- `medium`: one or more suspicious patterns worth checking.
- `high`: multiple suspicious patterns, especially payment-related names, generic UART identifiers, and strong nearby signal.

Recommended response: inspect the physical terminal only if authorized, preserve the AntEater report, and escalate through the site owner, payment processor, bank, or law enforcement as appropriate.
