# Meshtastic app on Heltec T114

The canonical Heltec Edition branch includes a Pi-side Meshtastic helper for status, node table, GPS/status information, protected listen mode, and protected send mode.

## Optional dependencies

Install the optional extras only when using Meshtastic/GNSS workflows:

```bash
python -m pip install -r pi-companion/requirements-heltec-v2-extra.txt
```

## Save a connection profile

Serial example:

```bash
python3 scripts/run_meshtastic_app.py setup --connection serial --port /dev/koalabyte-heltec
```

TCP example:

```bash
python3 scripts/run_meshtastic_app.py setup --connection tcp --host 192.168.1.50
```

BLE example:

```bash
python3 scripts/run_meshtastic_app.py setup --connection ble
```

## Check node status

```bash
python3 scripts/run_meshtastic_app.py status
python3 scripts/run_meshtastic_app.py nodes
python3 scripts/run_meshtastic_app.py gps
```

## Protected actions password

Sensitive location/listen/send actions use the protected-actions password gate:

```bash
python3 scripts/run_location_password_gate.py setup
python3 scripts/run_location_password_gate.py status
```

## Protected listen

```bash
python3 scripts/run_meshtastic_app.py listen --seconds 60 --prompt-password
```

## Protected send

Sending requires both the password gate and explicit confirmation:

```bash
python3 scripts/run_meshtastic_app.py send --message "KoalaByte test" --confirm-send --prompt-password
```

## GNSS helper

The GNSS helper can use a saved fix, environment variables, or Meshtastic info parsing, but coordinate logging remains gated.

Manual test fix:

```bash
export KOALABYTE_LOCATION_UNLOCKED=1
export KOALABYTE_GNSS_LAT=-33.8688
export KOALABYTE_GNSS_LON=151.2093
```

## Safety boundaries

- Use only on your own Meshtastic node or an authorized test mesh.
- Do not transmit to networks you do not operate or have permission to use.
- Keep location logging password-protected.
