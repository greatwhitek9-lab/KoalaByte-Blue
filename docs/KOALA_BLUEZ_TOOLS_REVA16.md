# RevA18 Outback BlueZ Module Deck

## Purpose

The Outback BlueZ Module Deck gives KoalaByte Blue a themed, safer automation layer around local Linux BlueZ tooling on the Raspberry Pi companion.

This replaces the plain RevA16 naming with KoalaByte-style module titles while keeping the same flash-ready repo layout:

- ESP32-S3 DualEye firmware remains under `firmware/esp32-dualeye/`
- Nordic BLE firmware remains dongle-only under `firmware/nrf52840-dongle-ear-tag-tx-lab/`
- Pi companion BlueZ automation remains under `pi-companion/koalablue/bluez_tools.py`
- Protected BlueZ lab actions live under `pi-companion/koalablue/bluez_protected_lab.py`
- Flash/readiness validation remains through `scripts/check_repo_readiness.py`

The module deck focuses on authorized local lab work:

- Local adapter inventory
- Local adapter status and optional D-Bus Adapter1 inspection through `busctl`
- Timed discovery with hashed/redacted addresses by default
- Timed `btmon` capture with `.btsnoop` artifact support
- Owned-device target information
- Owned-device service notes
- Owned-device GATT readiness checklist artifacts
- Protected lab-only helper actions for selected legacy BlueZ utilities
- A safe all-module sequence for pre-flash Pi companion validation

It does not perform pairing bypass, spoofing, disruptive link actions, captured-packet replay, or unknown-device GATT writes.

## Main runner

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py scan --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py monitor --duration 20
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py all-safe --duration 15
```

## Themed module titles

| KoalaByte title | Action | Backend | Purpose |
|---|---|---|---|
| Outback Module Deck | `manifest` | module manifest | Show the complete KoalaByte BlueZ catalog |
| Gumleaf Gear Check | `inventory` | PATH inventory | List installed local BlueZ helper tools |
| Eucalyptus Bus Scout | `status` | `bluetoothctl`, `btmgmt`, `rfkill`, optional `busctl` | Local adapter, controller, rfkill, and D-Bus status |
| Dropbear Discovery Sweep | `scan` | `bluetoothctl` timed discovery | Bounded BLE/BT discovery with redaction by default |
| Billabong HCI Watch | `monitor` | `btmon -w` | Bounded HCI monitor capture with `.btsnoop` artifact support |
| Joey Target Dossier | `info` | `bluetoothctl info` | Owned-device target information only |
| Treehouse Service Trace | `services` | `sdptool browse` | Owned-device service notes only |
| Gumnut GATT Gatecheck | `gatt-readiness` | checklist artifact | Safe checklist before any owned-device GATT review |
| Kookaburra Safe Nest Run | `all-safe` | module sequence | Inventory, status, and bounded discovery in one run |

## Protected lab-only BlueZ menu actions

These appear in the Bluetooth Tools and Authorized Lab menus. They are protected by the KoalaByte protected-actions password gate.

| KoalaByte menu name | Backend helper | Default behavior |
|---|---|---|
| Outback Radio Ledger | `hciconfig -a` | Protected local adapter ledger |
| Classic Track Finder | `hcitool dev` | Protected local classic-controller listing |
| Treehouse RFCOMM Wiremap | `rfcomm -a` | Protected RFCOMM binding/status map |
| Pouch Link Echo | `l2ping -c 1 <target>` | Protected single echo for an explicitly owned target |
| Gumnut GATT Ghostmap | `gatttool -b <target> --primary` | Protected primary service map for an explicitly owned target |

Set up the protected-actions password first:

```bash
PYTHONPATH=pi-companion python3 scripts/run_location_password_gate.py setup
```

Terminal menu mode prompts for the password when a protected BlueZ action is selected. Target-specific actions also require:

```bash
export KOALABYTE_BLUEZ_LAB_TARGET=AA:BB:CC:DD:EE:FF
export KOALABYTE_BLUEZ_OWNED_DEVICE=1
```

Without the password gate and owned-device target where required, the action writes a blocked artifact under `logs/koala_bluez/` and does not run the backend helper.

## Wrapped local BlueZ/helper tools

| KoalaByte helper name | Backend command | Purpose |
|---|---|---|
| Gumleaf Controller | `bluetoothctl` | Adapter power, discovery, and controller status |
| Eucalyptus Manager | `btmgmt` | Local controller management/status |
| Billabong HCI Watcher | `btmon` | Local HCI monitor capture/logging |
| Outback Radio Ledger | `hciconfig` | Local adapter identity/status when installed |
| Classic Track Finder | `hcitool` | Legacy local inquiry/controller support when installed |
| Branch Block Check | `rfkill` | Bluetooth soft/hard block status |
| Treehouse RFCOMM Notes | `rfcomm` | Local RFCOMM binding/status |
| Joey Service Notes | `sdptool` | Owned-device service browsing only |
| Pouch Link Echo | `l2ping` | Owned-device link echo only |
| Gumnut GATT Notes | `gatttool` | Legacy owned-device GATT observation when installed |
| Eucalyptus D-Bus Scout | `busctl` | Optional D-Bus Adapter1 introspection when installed |

## Convenience scripts

```bash
bash scripts/run_koala_bluez_manifest.sh
bash scripts/run_koala_bluez_inventory.sh
bash scripts/run_koala_bluez_status.sh
bash scripts/run_koala_bluez_scan.sh --duration 15
bash scripts/run_koala_bluez_monitor.sh --duration 20
bash scripts/run_koala_bluez_all_safe.sh --duration 15
bash scripts/run_koala_bluez_info.sh --target AA:BB:CC:DD:EE:FF --owned-device
bash scripts/run_koala_bluez_services.sh --target AA:BB:CC:DD:EE:FF --owned-device
bash scripts/run_koala_bluez_gatt_readiness.sh --target AA:BB:CC:DD:EE:FF --owned-device
```

## Menu entries

The main KoalaByte Blue Bluetooth Tools menu now lists the themed BlueZ modules:

```text
Outback Module Deck
Gumleaf Gear Check
Eucalyptus Bus Scout
Dropbear Discovery Sweep
Billabong HCI Watch
Kookaburra Safe Nest Run
Joey Target Dossier
Treehouse Service Trace
Gumnut GATT Gatecheck
Outback Radio Ledger
Classic Track Finder
Treehouse RFCOMM Wiremap
Pouch Link Echo
Gumnut GATT Ghostmap
```

## Output

Output is written to:

```text
logs/koala_bluez/
```

Typical files:

```text
koala_bluez_module_manifest.json
koala_bluez_inventory.json
koala_bluez_status_<timestamp>.json
koala_bluez_scan_<timestamp>.json
koala_bluez_monitor_<timestamp>.json
koala_bluez_btmon_<timestamp>.log
koala_bluez_btmon_<timestamp>.btsnoop
koala_bluez_gatt_readiness_<timestamp>.json
koala_bluez_outback_radio_ledger_<timestamp>.json
koala_bluez_classic_track_finder_<timestamp>.json
koala_bluez_treehouse_rfcomm_wiremap_<timestamp>.json
koala_bluez_pouch_link_echo_<timestamp>.json
koala_bluez_gumnut_gatt_ghostmap_<timestamp>.json
```

## Address handling

BlueZ module logs hash Bluetooth addresses by default. Use raw address logging only for owned devices, written-scope lab work, and local records:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py scan --duration 15 --raw-addresses
```

Raw address storage is intentionally explicit. The module safety manifest records whether raw addresses were requested.

## Target-specific diagnostics

Target-specific actions require both an explicit target and `--owned-device` for the direct runner:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py info --target AA:BB:CC:DD:EE:FF --owned-device
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py services --target AA:BB:CC:DD:EE:FF --owned-device
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py gatt-readiness --target AA:BB:CC:DD:EE:FF --owned-device
```

Without `--owned-device`, the target-specific module writes a blocked summary artifact instead of running the target operation.

## Install notes

Install core packages on Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y bluetooth bluez bluez-tools rfkill
```

Optional utilities that may be present on some images:

```text
btmgmt btmon hciconfig hcitool sdptool rfcomm l2ping gatttool busctl
```

Some older BlueZ utilities are deprecated and may not exist on every OS image. `Gumleaf Gear Check` records which helpers are actually present so the repo can remain flash-ready across clean Pi images.
