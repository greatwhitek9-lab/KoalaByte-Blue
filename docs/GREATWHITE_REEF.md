# GreatWhite Reef

GreatWhite Reef is the KoalaByte Blue wrapped packet-analysis submenu.

## Tool names

| KoalaByte name | Upstream tool | Purpose |
|---|---|---|
| TigerShark | `tshark` | Terminal packet-analysis and PCAP/PCAPNG review helper. |
| Great Wire Shark | `wireshark` | GUI packet-analysis review helper. |

## Wrapped submenu actions

Every action is selectable from the KoalaByte wrapped menu UI. No shell typing is required from the menu.

| Menu item | Command | What it does |
|---|---|---|
| Reef Status | `greatwhite_reef_status` | Shows TigerShark / Great Wire Shark readiness, sync status, PCAP count, and the PCAP folder path. |
| TigerShark Install Check | `greatwhite_tigershark_check` | Checks whether `tshark` and `wireshark` are installed. |
| TigerShark Interfaces | `greatwhite_tigershark_interfaces` | Lists local `tshark -D` interfaces for lab planning. |
| TigerShark PCAP Folder | `greatwhite_tigershark_pcap_folder` | Creates and syncs `logs/greatwhite_reef/pcaps/` for owned-device or written-scope PCAPs. |
| TigerShark Read Latest PCAP | `greatwhite_tigershark_read_latest` | Runs TigerShark Read on the newest `.pcap` / `.pcapng` in the PCAP folder. |
| `PCAP 1: <file>` | `greatwhite_pcap_read:<file>` | Dynamic row. Highlight/select this exact PCAP and run it through TigerShark Read. |
| `PCAP 2: <file>` | `greatwhite_pcap_read:<file>` | Dynamic row for the next newest PCAP. Additional PCAP rows are generated automatically. |
| Great Wire Shark Launch Notes | `great_wire_shark_launch_notes` | Writes GUI review notes for opening the latest PCAP in Great Wire Shark / Wireshark. |
| Great Wire Shark Folder Notes | `great_wire_shark_folder_notes` | Writes folder-review notes for the Great Wire Shark workflow. |
| GreatWhite Reef Report | `greatwhite_reef_report` | Builds a defensive packet-analysis report artifact. |

## Automatic PCAP sync

GreatWhite Reef keeps the review folder here:

```text
logs/greatwhite_reef/pcaps/
```

When GreatWhite Reef opens or runs a Reef action, it looks for `.pcap` and `.pcapng` files under `logs/` and copies them into `logs/greatwhite_reef/pcaps/` if they are not already there.

You can add more import folders with:

```bash
export KOALABYTE_REEF_PCAP_IMPORT_DIRS="/path/to/extra/pcaps:/another/folder"
```

## Selectable PCAP rows

The GreatWhite Reef submenu refreshes its PCAP rows dynamically. Files appear newest first:

```text
PCAP 1: latest_capture.pcapng
PCAP 2: older_capture.pcap
PCAP 3: another_capture.pcapng
```

Highlight a PCAP row with the K1-K8 front-panel buttons, touchscreen, keyboard, or voice command, then select it. The selected file runs through TigerShark Read automatically and writes JSON output under:

```text
logs/greatwhite_reef/
```

Example voice patterns:

```text
killerkoala open GreatWhite Reef
killerkoala run PCAP 1
killerkoala run PCAP 2
killerkoala run TigerShark Read Latest PCAP
```

## Install hint

```bash
sudo apt update
sudo apt install -y tshark wireshark
```

## Boundary

GreatWhite Reef is for local, owned-device, or written-scope packet analysis. It creates local JSON and Markdown artifacts under `logs/greatwhite_reef/`.
