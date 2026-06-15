# RevA12 Menu Selection Screen / RevA21 Koala Mode Update

## Purpose

The menu layer gives KoalaByte Blue a single selection screen that can be driven by:

- Six front-panel GPIO buttons.
- Touchscreen drag scrolling.
- Touchscreen long-press select.
- Keyboard input during development.
- RevA14 large bubbly jungle/eucalyptus graphical rendering.
- RevA15 Koala Kry RF Review safe manifest path.
- RevA15 KoalaByte Lab synthetic owned-device advertisement workflow.
- RevA16 Koala BlueZ local helper workflows.
- RevA17 killerkoala voice/vocabulary preview.
- RevA21 Koala Mode Switcher for selecting KoalaByte Lab or Koala Konnect.

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
13 KoalaByte Lab              Synthetic owned-device BLE advertisement observation workflow
14 Koala Mode Switcher        Build/package/select KoalaByte Lab or Koala Konnect
15 Gumleaf Gear Check         Inventory installed BlueZ helper tools
16 Eucalyptus Bus Scout       Save local Bluetooth/BlueZ adapter status
17 Dropbear Discovery Sweep   Run timed local discovery and save results
18 Billabong HCI Watch        Run timed local HCI monitor logging
19 Kookaburra Safe Nest Run   Run safe BlueZ helper sequence
20 KillerKoala Voice          Preview event reactions and inquiry vocabulary by XP rank
21 Urban Poaching             Authorized BLE RSSI lab game
22 Buttons                    Show/check GPIO front-panel button status
23 Level / Status             Show XP and rank
24 Report                     Write a Markdown session report
25 Wake killerkoala           Test wake-word flow
26 Authorized BLE Inventory   Create a lab inventory from passive BLE observations
27 GATT Readiness Checklist   Generate a pre-test checklist for owned-device GATT review
28 Pairing Security Review    Review pairing and access-control posture for owned lab devices
29 Lab Beacon Plan            Create a safe ESP32 demo beacon/peripheral testing plan
30 Packet Capture Notes       Create safe Wireshark/nRF52840 protocol-analysis notes
31 Defensive Lab Report       Generate a defensive lab report template
32 Restricted Placeholder     Locked/non-operational reserved slot
33 Settings                   Device and companion settings
34 Lab                        Password-gated Authorized Lab Use menu
35 Shutdown                   Confirm safe shutdown
36 Quit                       Exit the Pi companion UI
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

## RevA21 mode switcher entry

The `Koala Mode Switcher` entry points to:

```text
pi-companion/koalablue/koala_mode_switcher.py
scripts/run_koala_mode_switcher.py
```

Useful commands:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare-all
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
