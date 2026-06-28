from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Type, TypeVar

T = TypeVar("T")

MENU_GROUPS: List[str] = [
    "Bluetooth Tools",
    "Didgeridoo",
    "CAN Bench Tools",
    "Reports & Reviews",
    "System / Companion",
]

_GROUP_ORDER = {name: index for index, name in enumerate(MENU_GROUPS)}

MAIN_MENU_ITEMS: List[dict[str, object]] = [
    {"group": "Bluetooth Tools", "label": "Eucalyptus", "command": "submenu:eucalyptus", "description": "Open the eucalyptus canopy submenu for passive BLE logger controls"},
    {"group": "Bluetooth Tools", "label": "Koala Kombat Kruisin’", "command": "submenu:kruisin", "description": "Open passive Wi-Fi/BLE/GPS survey mapping and WiGLE export tools"},
    {"group": "Bluetooth Tools", "label": "Bluetooth Tools", "command": "submenu:bluetooth", "description": "Open the jungle Bluetooth tool chest"},
    {"group": "Didgeridoo", "label": "Didgeridoo", "command": "submenu:didgeridoo", "description": "Open the Didgeridoo mesh app for T114 BLE, primary GNSS, Meshtastic, and protected location helpers"},
    {"group": "CAN Bench Tools", "label": "CAN Bench Tools", "command": "submenu:can_bench", "description": "Open isolated Koala Kan bench and simulator checks"},
    {"group": "Reports & Reviews", "label": "Reports & Reviews", "command": "submenu:reports", "description": "Open reports, reviews, and defensive notes"},
    {"group": "System / Companion", "label": "System / Companion", "command": "submenu:system", "description": "Open companion, voice, buttons, settings, and mode helpers"},
    {"group": "System / Companion", "label": "Lab", "command": "submenu:lab", "description": "Open the Authorized Lab Use submenu"},
    {"group": "System / Companion", "label": "Power & Exit", "command": "submenu:power", "description": "Open shutdown and quit controls"},
]

SUBMENU_ITEMS: Dict[str, List[dict[str, object]]] = {
    "eucalyptus": [
        {"group": "Bluetooth Tools", "label": "Eucalyptus Canopy Status", "command": "eucalyptus status", "description": "Show passive BLE, GPS, and WiGLE readiness status"},
        {"group": "Bluetooth Tools", "label": "Eucalyptus Canopy Start", "command": "eucalyptus start", "description": "Start or record always-on passive BLE logging"},
        {"group": "Bluetooth Tools", "label": "Eucalyptus Canopy Stop", "command": "eucalyptus stop", "description": "Stop or record always-on passive BLE logging"},
        {"group": "Bluetooth Tools", "label": "Eucalyptus Canopy Restart", "command": "eucalyptus restart", "description": "Restart or record always-on passive BLE logging"},
        {"group": "Bluetooth Tools", "label": "Eucalyptus GPS Trail", "command": "eucalyptus gps-trail", "description": "Build a GPS-enriched passive BLE trail from discovered devices"},
        {"group": "Bluetooth Tools", "label": "Eucalyptus Upload Trail", "command": "eucalyptus upload-status", "description": "Show GPS/WiGLE upload readiness and status"},
        {"group": "Bluetooth Tools", "label": "Eucalyptus WiGLE Upload", "command": "eucalyptus wigle-upload", "description": "Upload GPS-tagged passive BLE observations to WiGLE when explicitly armed"},
        {"group": "Bluetooth Tools", "label": "Eucalyptus Koalagotchi Mode", "command": "eucalyptus_mode", "description": "Open the Koalagotchi always-on Bluetooth scanner/logger screen"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
    "kruisin": [
        {"group": "Bluetooth Tools", "label": "Kruisin’ Status", "command": "kruisin status", "description": "Show Wi-Fi/BLE/GPS survey and WiGLE readiness"},
        {"group": "Bluetooth Tools", "label": "Wi-Fi AP Survey", "command": "kruisin wifi-survey", "description": "Run a passive Wi-Fi access point survey with RSSI and optional GPS"},
        {"group": "Bluetooth Tools", "label": "BLE Survey", "command": "kruisin ble-survey", "description": "Run a passive BLE survey with RSSI and optional GPS"},
        {"group": "Bluetooth Tools", "label": "Wi-Fi + BLE Survey", "command": "kruisin survey", "description": "Run combined passive Wi-Fi/BLE survey and write mapping artifacts"},
        {"group": "Didgeridoo", "label": "Kruisin’ GPS Status", "command": "kruisin gps-status", "description": "Show protected GNSS/fixed lab coordinate readiness for survey mapping"},
        {"group": "Reports & Reviews", "label": "Kruisin’ Export Files", "command": "kruisin export", "description": "Export survey JSONL, CSV, GeoJSON, and WiGLE CSV files"},
        {"group": "Reports & Reviews", "label": "Kruisin’ WiGLE Upload", "command": "kruisin wigle-upload", "description": "Upload Wi-Fi/BLE survey data to WiGLE when explicitly armed"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
    "bluetooth": [
        {"group": "Bluetooth Tools", "label": "Scan", "command": "scan", "description": "Run a safe local BLE inventory scan"},
        {"group": "Bluetooth Tools", "label": "Summary", "command": "summary", "description": "Summarize observed local BLE devices"},
        {"group": "Bluetooth Tools", "label": "Show Devices", "command": "show", "description": "Show the current local BLE device table"},
        {"group": "Bluetooth Tools", "label": "Koala Kapture", "command": "koala_kapture", "description": "Record authorized lab observation metadata"},
        {"group": "Bluetooth Tools", "label": "Koala Kry", "command": "koala_kry", "description": "Replay local saved metadata into the report pipeline"},
        {"group": "Bluetooth Tools", "label": "Ear Tag", "command": "ear_tag", "description": "Named lab BLE beacon"},
        {"group": "Bluetooth Tools", "label": "KoalaByte Lab", "command": "ear_tag_tx_lab", "description": "Synthetic owned-device BLE lab advertisement"},
        {"group": "Bluetooth Tools", "label": "Outback Module Deck", "command": "koala_bluez_manifest", "description": "Show the complete KoalaByte BlueZ module manifest"},
        {"group": "Bluetooth Tools", "label": "Gumleaf Gear Check", "command": "koala_bluez_inventory", "description": "Inventory local BlueZ helpers"},
        {"group": "Bluetooth Tools", "label": "Eucalyptus Bus Scout", "command": "koala_bluez_status", "description": "Collect local adapter and controller status"},
        {"group": "Bluetooth Tools", "label": "Dropbear Discovery Sweep", "command": "koala_bluez_scan", "description": "Run bounded local discovery with safe defaults"},
        {"group": "Bluetooth Tools", "label": "Billabong HCI Watch", "command": "koala_bluez_monitor", "description": "Run bounded local HCI capture"},
        {"group": "Bluetooth Tools", "label": "Kookaburra Safe Nest Run", "command": "koala_bluez_all_safe", "description": "Run local inventory, status, and bounded discovery"},
        {"group": "Bluetooth Tools", "label": "Joey Target Dossier", "command": "koala_bluez_info", "description": "Protected lab-only owned-device target info card"},
        {"group": "Bluetooth Tools", "label": "Treehouse Service Trace", "command": "koala_bluez_services", "description": "Protected lab-only owned-device service notes"},
        {"group": "Bluetooth Tools", "label": "Gumnut GATT Gatecheck", "command": "koala_bluez_gatt_readiness", "description": "Protected lab-only owned-device GATT readiness checklist"},
        {"group": "Bluetooth Tools", "label": "Outback Radio Ledger", "command": "bluez_outback_radio_ledger", "description": "Protected lab-only local adapter ledger using hciconfig when installed"},
        {"group": "Bluetooth Tools", "label": "Classic Track Finder", "command": "bluez_classic_track_finder", "description": "Protected lab-only classic controller listing using hcitool when installed"},
        {"group": "Bluetooth Tools", "label": "Treehouse RFCOMM Wiremap", "command": "bluez_treehouse_rfcomm_wiremap", "description": "Protected lab-only RFCOMM binding/status map using rfcomm when installed"},
        {"group": "Bluetooth Tools", "label": "Pouch Link Echo", "command": "bluez_pouch_link_echo", "description": "Protected lab-only single owned-device link echo using l2ping when installed"},
        {"group": "Bluetooth Tools", "label": "Gumnut GATT Ghostmap", "command": "bluez_gumnut_gatt_ghostmap", "description": "Protected lab-only owned-device primary GATT service map using gatttool when installed"},
        {"group": "Bluetooth Tools", "label": "Platypus BT-Proxy", "command": "bluez_platypus_bt_proxy", "description": "Protected lab-only btproxy readiness check; no proxy session is started"},
        {"group": "Bluetooth Tools", "label": "that’s not a knife", "command": "thats_not_a_knife", "description": "that’s not a knife defensive local BLE pressure guard"},
        {"group": "Bluetooth Tools", "label": "AntEater", "command": "anteater", "description": "Passive BLE payment-terminal risk triage with redacted reports"},
        {"group": "Bluetooth Tools", "label": "Urban Poaching", "command": "urban_poaching", "description": "Authorized BLE RSSI lab game"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
    "didgeridoo": [
        {"group": "Didgeridoo", "label": "Heltec Link", "command": "status:t114_link", "description": "Constant status: connected or disconnected."},
        {"group": "Didgeridoo", "label": "Radio/GPS", "command": "status:t114_radio_gps", "description": "Constant status: current Heltec BLE and GPS state."},
        {"group": "Didgeridoo", "label": "T114 Quick BLE Test Scan", "command": "t114_primary_ble_scan", "description": "Run bounded passive BLE test scan through the T114 nRF52840 primary radio"},
        {"group": "Didgeridoo", "label": "Lab Beacon TX", "command": "status:t114_tx", "description": "Constant status: safe lab beacon transmit mode is on, off, or blocked."},
        {"group": "Didgeridoo", "label": "Sextant", "command": "t114_primary_gnss_fix", "description": "Get the current GPS/GNSS location from the Heltec T114 stream"},
        {"group": "Didgeridoo", "label": "Didgeridoo Status", "command": "meshtastic_status", "description": "Show local Meshtastic node status through the Didgeridoo app"},
        {"group": "Didgeridoo", "label": "Didgeridoo Nodes", "command": "meshtastic_nodes", "description": "Show the Meshtastic node table through the Didgeridoo app"},
        {"group": "Didgeridoo", "label": "Didgeridoo GPS Info", "command": "meshtastic_gps", "description": "Show GPS/GNSS status from the connected Meshtastic node through the Didgeridoo app"},
        {"group": "Didgeridoo", "label": "Protected Location Gate Status", "command": "location_gate_status", "description": "Show protected-actions password gate state before location-sensitive Didgeridoo actions"},
        {"group": "Didgeridoo", "label": "Protected GNSS Current Fix", "command": "gnss_current_fix", "description": "Show current GNSS fix only when the protected-actions gate is unlocked"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
    "can_bench": [
        {"group": "CAN Bench Tools", "label": "Koala Kan Kommander", "command": "koala_kan_kommander", "description": "InnoMaker USB-to-CAN listen and gated bench-simulator workflow"},
        {"group": "CAN Bench Tools", "label": "CAN Bench Safety Check", "command": "koala_kan_kommander", "description": "Open Koala Kan safe manifest/inventory/status workflow"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
    "reports": [
        {"group": "Reports & Reviews", "label": "Koala Kry RF Review", "command": "koala_kry_transmit_review", "description": "Write RF bench isolation and authorization review; no RF is sent"},
        {"group": "Reports & Reviews", "label": "Report", "command": "report", "description": "Write a Markdown session report"},
        {"group": "Reports & Reviews", "label": "Boomerang", "command": "boomerang", "description": "Boomerang camera-awareness logbook; manual public observations; stays open until quit"},
        {"group": "Reports & Reviews", "label": "Authorized BLE Inventory", "command": "authorized_ble_inventory", "description": "Create a lab inventory from local observations"},
        {"group": "Reports & Reviews", "label": "GATT Readiness Checklist", "command": "gatt_readiness_checklist", "description": "Generate a pre-test checklist for owned-device GATT review"},
        {"group": "Reports & Reviews", "label": "Pairing Security Review", "command": "pairing_security_review", "description": "Review owned-device pairing/access-control posture"},
        {"group": "Reports & Reviews", "label": "Lab Beacon Plan", "command": "lab_beacon_plan", "description": "Create a safe ESP32 demo beacon/peripheral testing plan"},
        {"group": "Reports & Reviews", "label": "Packet Capture Notes", "command": "packet_capture_notes", "description": "Create protocol-analysis notes"},
        {"group": "Reports & Reviews", "label": "Defensive Lab Report", "command": "defensive_report", "description": "Generate a defensive lab report template"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
    "system": [
        {"group": "System / Companion", "label": "Koala Mode Switcher", "command": "koala_mode_switcher", "description": "Build/package/select KoalaByte Lab or Koala Konnect for the legacy nRF52840 dongle path"},
        {"group": "System / Companion", "label": "KillerKoala Voice", "command": "killerkoala_voice", "description": "Preview event reactions and vocabulary by XP rank"},
        {"group": "System / Companion", "label": "Buttons", "command": "buttons", "description": "Show/check GPIO front-panel button status"},
        {"group": "System / Companion", "label": "Level / Status", "command": "level/status", "description": "Show XP and rank"},
        {"group": "System / Companion", "label": "Wake killerkoala", "command": "wake killerkoala", "description": "Test wake-word flow"},
        {"group": "System / Companion", "label": "Restricted Placeholder", "command": "restricted_placeholder", "description": "Reserved locked slot; intentionally non-operational", "enabled": False},
        {"group": "System / Companion", "label": "Settings", "command": "settings", "description": "Device and companion settings"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
    "lab": [
        {"group": "Reports & Reviews", "label": "Authorized BLE Inventory", "command": "authorized_ble_inventory", "description": "Create a lab inventory from local observations"},
        {"group": "Reports & Reviews", "label": "GATT Readiness Checklist", "command": "gatt_readiness_checklist", "description": "Generate a pre-test checklist for owned-device GATT review"},
        {"group": "Reports & Reviews", "label": "Pairing Security Review", "command": "pairing_security_review", "description": "Review owned-device pairing/access-control posture"},
        {"group": "Reports & Reviews", "label": "Lab Beacon Plan", "command": "lab_beacon_plan", "description": "Create a safe ESP32 demo beacon/peripheral testing plan"},
        {"group": "CAN Bench Tools", "label": "CAN Bench Safety Check", "command": "koala_kan_kommander", "description": "Open Koala Kan safe manifest/inventory/status workflow"},
        {"group": "Bluetooth Tools", "label": "Joey Target Dossier", "command": "koala_bluez_info", "description": "Protected lab-only owned-device target info card"},
        {"group": "Bluetooth Tools", "label": "Treehouse Service Trace", "command": "koala_bluez_services", "description": "Protected lab-only owned-device service notes"},
        {"group": "Bluetooth Tools", "label": "Gumnut GATT Gatecheck", "command": "koala_bluez_gatt_readiness", "description": "Protected lab-only owned-device GATT readiness checklist"},
        {"group": "Bluetooth Tools", "label": "Outback Radio Ledger", "command": "bluez_outback_radio_ledger", "description": "Protected lab-only local adapter ledger"},
        {"group": "Bluetooth Tools", "label": "Classic Track Finder", "command": "bluez_classic_track_finder", "description": "Protected lab-only classic controller listing"},
        {"group": "Bluetooth Tools", "label": "Treehouse RFCOMM Wiremap", "command": "bluez_treehouse_rfcomm_wiremap", "description": "Protected lab-only RFCOMM binding/status map"},
        {"group": "Bluetooth Tools", "label": "Pouch Link Echo", "command": "bluez_pouch_link_echo", "description": "Protected lab-only single owned-device link echo"},
        {"group": "Bluetooth Tools", "label": "Gumnut GATT Ghostmap", "command": "bluez_gumnut_gatt_ghostmap", "description": "Protected lab-only owned-device primary GATT service map"},
        {"group": "Bluetooth Tools", "label": "Platypus BT-Proxy", "command": "bluez_platypus_bt_proxy", "description": "Protected lab-only btproxy readiness check"},
        {"group": "Didgeridoo", "label": "Protected Location Gate Status", "command": "location_gate_status", "description": "Show protected-actions password gate state"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
    "power": [
        {"group": "System / Companion", "label": "Shutdown", "command": "shutdown_confirm", "description": "Confirm safe shutdown"},
        {"group": "System / Companion", "label": "Quit", "command": "quit", "description": "Exit the Pi companion UI"},
        {"group": "System / Companion", "label": "Back to Main Canopy", "command": "submenu:main", "description": "Return to the main KoalaByte Blue menu"},
    ],
}

FUNCTION_MENU_ITEMS = MAIN_MENU_ITEMS


def submenu_name_from_command(command: str) -> str:
    return command.split(":", 1)[1].strip().lower() if command.startswith("submenu:") else ""


def submenu_title(menu_name: str) -> str:
    titles = {
        "main": "Main Canopy",
        "eucalyptus": "Eucalyptus",
        "kruisin": "Koala Kombat Kruisin’",
        "bluetooth": "Bluetooth Tools",
        "didgeridoo": "Didgeridoo",
        "can_bench": "CAN Bench Tools",
        "reports": "Reports & Reviews",
        "system": "System / Companion",
        "lab": "Authorized Lab",
        "power": "Power & Exit",
    }
    return titles.get(menu_name, menu_name.replace("_", " ").title())


def _entries_for_menu(menu_name: str = "main") -> List[dict[str, object]]:
    return MAIN_MENU_ITEMS if menu_name == "main" else SUBMENU_ITEMS.get(menu_name, [])


def all_menu_entries() -> List[dict[str, object]]:
    entries: List[dict[str, object]] = list(MAIN_MENU_ITEMS)
    for submenu_entries in SUBMENU_ITEMS.values():
        entries.extend(submenu_entries)
    return entries


def leaf_menu_entries() -> List[dict[str, object]]:
    return [entry for entry in all_menu_entries() if not str(entry.get("command", "")).startswith("submenu:") and bool(entry.get("enabled", True))]


def _entry_group(entry: dict[str, object]) -> str:
    group = str(entry.get("group", "System / Companion"))
    return group if group in _GROUP_ORDER else "System / Companion"


def grouped_entries(menu_name: str = "main") -> Dict[str, List[dict[str, object]]]:
    groups: Dict[str, List[str]] | Dict[str, List[dict[str, object]]] = OrderedDict((name, []) for name in MENU_GROUPS)
    for entry in _entries_for_menu(menu_name):
        groups[_entry_group(entry)].append(entry)  # type: ignore[index]
    return groups  # type: ignore[return-value]


def sorted_menu_entries(menu_name: str = "main") -> List[dict[str, object]]:
    indexed = list(enumerate(_entries_for_menu(menu_name)))
    indexed.sort(key=lambda pair: (_GROUP_ORDER[_entry_group(pair[1])], pair[0]))
    return [entry for _idx, entry in indexed]


def make_menu_items(menu_item_cls: Type[T], menu_name: str = "main") -> List[T]:
    items: List[T] = []
    for entry in sorted_menu_entries(menu_name):
        kwargs = {"label": str(entry["label"]), "command": str(entry["command"]), "description": str(entry.get("description", "")), "enabled": bool(entry.get("enabled", True)), "group": _entry_group(entry)}
        try:
            items.append(menu_item_cls(**kwargs))
        except TypeError:
            kwargs.pop("group", None)
            try:
                items.append(menu_item_cls(**kwargs))
            except TypeError:
                kwargs.pop("enabled", None)
                items.append(menu_item_cls(**kwargs))
    return items


def menu_labels(menu_name: str = "main") -> List[str]:
    return [str(item["label"]) for item in _entries_for_menu(menu_name)]


def grouped_menu_labels(menu_name: str = "main") -> Dict[str, List[str]]:
    return {group: [str(item["label"]) for item in entries] for group, entries in grouped_entries(menu_name).items()}
