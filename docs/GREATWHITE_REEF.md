# GreatWhite Reef

GreatWhite Reef is the KoalaByte Blue wrapped packet-analysis submenu.

## Tool names

| KoalaByte name | Upstream tool | Purpose |
|---|---|---|
| TigerShark | `tshark` | Terminal packet-analysis and PCAP review helper. |
| Great Wire Shark | `wireshark` | GUI packet-analysis review helper. |

## Wrapped submenu actions

Every action is selectable from the KoalaByte wrapped menu UI. No shell typing is required from the menu.

| Menu item | Command | What it does |
|---|---|---|
| Reef Status | `greatwhite_reef_status` | Shows TigerShark / Great Wire Shark readiness and the PCAP folder path. |
| TigerShark Install Check | `greatwhite_tigershark_check` | Checks whether `tshark` and `wireshark` are installed. |
| TigerShark Interfaces | `greatwhite_tigershark_interfaces` | Lists local `tshark -D` interfaces for lab planning. |
| TigerShark PCAP Folder | `greatwhite_tigershark_pcap_folder` | Creates `logs/greatwhite_reef/pcaps/` for owned-device or written-scope PCAPs. |
| TigerShark Read Latest PCAP | `greatwhite_tigershark_read_latest` | Runs a bounded local summary of the newest `.pcap` / `.pcapng` in the PCAP folder. |
| Great Wire Shark Launch Notes | `great_wire_shark_launch_notes` | Writes GUI review notes for opening the latest PCAP in Wireshark. |
| Great Wire Shark Folder Notes | `great_wire_shark_folder_notes` | Writes folder-review notes for the Great Wire Shark workflow. |
| GreatWhite Reef Report | `greatwhite_reef_report` | Builds a defensive packet-analysis report artifact. |

## PCAP folder

```text
logs/greatwhite_reef/pcaps/
```

Drop owned-device or written-scope `.pcap` / `.pcapng` files there, then run **TigerShark Read Latest PCAP** from the menu.

## Install hint

```bash
sudo apt update
sudo apt install -y tshark wireshark
```

## Boundary

GreatWhite Reef is for local, owned-device, or written-scope packet analysis. It creates local JSON and Markdown artifacts under `logs/greatwhite_reef/`.
