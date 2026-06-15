# RevA8 eucalyptus Always-On BLE Scanner/Logger

## Action name

The always-on passive Bluetooth/BLE scanner/logger action is named:

```text
eucalyptus
```

## Purpose

`eucalyptus` is KoalaByte Blue's passive always-on Bluetooth/BLE observation mode for authorized lab use. It continuously scans nearby BLE advertisements, records observations locally, and can prepare compatible records for WiGLE upload when credentials and location settings are configured.

## Default storage

```text
/blecaptures/
```

## Config keys

See `pi-companion/config.default.json`:

```json
{
  "action_names": {
    "always_on_ble_scanner_logger": "eucalyptus"
  },
  "eucalyptus": {
    "display_name": "eucalyptus",
    "enabled": true,
    "capture_dir": "/blecaptures",
    "mode": "passive_ble_observation"
  }
}
```

## Console naming

Use the name `eucalyptus` in UI menus, docs, logs, and future CLI commands for the always-on BLE scanner/logger action.

Suggested commands for future CLI integration:

```text
eucalyptus status
eucalyptus start
eucalyptus stop
eucalyptus restart
eucalyptus upload-status
```

## Safety boundary

`eucalyptus` is passive observation and logging only. It is not a connection, pairing, disruption, or access workflow.
