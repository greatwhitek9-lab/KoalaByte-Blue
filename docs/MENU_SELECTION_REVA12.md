# RevA12 Menu Selection Screen / RevA17 killerkoala Voice Update

## Purpose

The menu layer gives KoalaByte Blue a single selection screen that can be driven by:

- Six front-panel GPIO buttons.
- Touchscreen drag scrolling.
- Touchscreen long-press select.
- Keyboard input during development.
- RevA14 large bubbly jungle/eucalyptus graphical rendering.
- RevA15 Koala Kry RF Review safe manifest path.
- RevA15 Ear Tag TX Lab synthetic owned-device advertisement workflow.
- RevA16 Koala BlueZ local helper workflows.
- RevA17 killerkoala voice/vocabulary preview.

## Full function menu

The default menu is generated from one shared catalog:

```text
pi-companion/koalablue/menu_catalog.py
```

That catalog is consumed by:

```text
pi-companion/koalablue/menu_ui.py
pi-companion/koalablue/menu_screen.py
pi-companion/koalablue/menu_theme.py
```

Default menu entries:

```text
01 Scan                       Run a safe BLE inventory scan
02 Summary                    Summarize observed BLE devices
03 Show Devices               Show the current BLE device table
04 eucalyptus Status          Show always-on BLE logger status
05 eucalyptus Start           Start always-on passive BLE logging
06 eucalyptus Stop            Stop always-on passive BLE logging
07 eucalyptus Restart         Restart always-on passive BLE logging
08 eucalyptus Upload Status   Show WiGLE upload readiness/status
09 Koala Kapture              Capture and archive BLE advertisement metadata
10 Koala Kry                  Replay captured metadata offline into the report/XP pipeline
11 Koala Kry RF Review        Write blocked RF review manifest; no RF is sent
12 Ear Tag                    Named lab BLE beacon
13 Ear Tag TX Lab             Synthetic owned-device BLE advertisement observation workflow
14 Koala BlueZ Inventory      List installed local BlueZ helper tools
15 Koala BlueZ Status         Save local Bluetooth/BlueZ adapter status
16 Koala BlueZ Scan           Run timed local discovery and save results
17 Koala BlueZ Monitor        Run timed local HCI monitor logging
18 KillerKoala Voice          Preview event reactions and inquiry vocabulary by XP rank
19 Urban Poaching             Authorized BLE RSSI lab game
20 Buttons                    Show/check GPIO front-panel button status
21 Level / Status             Show XP and rank
22 Report                     Write a Markdown session report
23 Wake killerkoala           Test wake-word flow
24 Authorized BLE Inventory   Create a lab inventory from passive BLE observations
25 GATT Readiness Checklist   Generate a pre-test checklist for owned-device GATT review
26 Pairing Security Review    Review pairing and access-control posture for owned lab devices
27 Lab Beacon Plan            Create a safe ESP32 demo beacon/peripheral testing plan
28 Packet Capture Notes       Create safe Wireshark/nRF52840 protocol-analysis notes
29 Defensive Lab Report       Generate a defensive lab report template
30 Restricted Placeholder     Locked/non-operational reserved slot
31 Settings                   Device and companion settings
32 Lab                        Password-gated Authorized Lab Use menu
33 Shutdown                   Confirm safe shutdown
34 Quit                       Exit the Pi companion UI
```

## RevA17 killerkoala voice entry

The `KillerKoala Voice` entry points to:

```text
pi-companion/koalablue/killerkoala_vocabulary.py
scripts/run_killerkoala_voice.py
```

Use the runner directly:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py scan_start --xp 100
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py --manifest
```

## RevA14 visual theme

The menu selection screen has a jungle/eucalyptus visual theme:

```text
large rounded bubbly menu item font
eucalyptus branch border
leaf accents on the selected row
rounded pill-style menu rows
touch-ready graphical renderer
terminal eucalyptus branch preview
```

Theme implementation:

```text
pi-companion/koalablue/menu_theme.py
```

The renderer uses system fonts only. It tries rounded/bubbly font candidates when present and falls back to DejaVu Sans. No external font files are bundled.

## Button mapping

```text
Button 1 = Main Menu
Button 2 = Left / Back / Previous item
Button 3 = Select; hold for Shutdown
Button 4 = Right / Forward / Next item
Button 5 = Up / Previous item
Button 6 = Down / Next item
```

## Test from terminal

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

Keyboard test controls:

```text
w = up
s = down
a = left/back/previous
d = right/forward/next
Enter = select
m = main menu
q = quit
```

## Event log

Menu events are logged locally:

```text
logs/menu_events.jsonl
```

## Safety scope

The menu only routes local UI actions. Sensitive lab features should continue to use the password-gated authorized lab menu and existing safe-mode boundaries. Locked entries remain non-operational until intentionally implemented under the safe lab policy.
