from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Type, TypeVar

T = TypeVar("T")

MENU_GROUPS: List[str] = ["Bluetooth Tools", "Didgeridoo", "CAN Bench Tools", "Reports & Reviews", "System / Companion"]
_GROUP_ORDER = {name: index for index, name in enumerate(MENU_GROUPS)}


def _item(group: str, label: str, command: str, description: str = "", enabled: bool = True) -> dict[str, object]:
    row: dict[str, object] = {"group": group, "label": label, "command": command, "description": description}
    if enabled is not True:
        row["enabled"] = enabled
    return row


MAIN_MENU_ITEMS: List[dict[str, object]] = [
    _item("Bluetooth Tools", "Eucalyptus", "submenu:eucalyptus", "Open Eucalyptus passive logger controls"),
    _item("Bluetooth Tools", "Koala Kombat Kruisin’", "submenu:kruisin", "Open passive Wi-Fi/BLE/GPS survey mapping and WiGLE tools"),
    _item("Bluetooth Tools", "Bluetooth Tools", "submenu:bluetooth", "Open the jungle Bluetooth tool chest"),
    _item("Didgeridoo", "Didgeridoo", "submenu:didgeridoo", "Open T114 BLE, GNSS, Meshtastic, and location helpers"),
    _item("CAN Bench Tools", "CAN Bench Tools", "submenu:can_bench", "Open Koala Kan bench checks"),
    _item("Reports & Reviews", "Reports & Reviews", "submenu:reports", "Open reports, reviews, and notes"),
    _item("System / Companion", "System / Companion", "submenu:system", "Open companion, voice, buttons, settings, and modes"),
    _item("System / Companion", "Lab", "submenu:lab", "Open the Authorized Lab Use submenu"),
    _item("System / Companion", "Power & Exit", "submenu:power", "Open shutdown and quit controls"),
]

SUBMENU_ITEMS: Dict[str, List[dict[str, object]]] = {
    "eucalyptus": [
        _item("Bluetooth Tools", "Eucalyptus Prompt Status", "eucalyptus_prompt_status", "Show saved GPS/WiGLE prompt state"),
        _item("Bluetooth Tools", "Eucalyptus GPS ON", "eucalyptus_gps_on", "Enable GPS enrichment from the menu"),
        _item("Bluetooth Tools", "Eucalyptus GPS OFF", "eucalyptus_gps_off", "Disable GPS enrichment from the menu"),
        _item("Bluetooth Tools", "Eucalyptus WiGLE Dry-Run ON", "eucalyptus_wigle_dry_run_on", "Build WiGLE CSV without uploading"),
        _item("Bluetooth Tools", "Eucalyptus WiGLE Dry-Run OFF", "eucalyptus_wigle_dry_run_off", "Allow real upload when armed and credentials exist"),
        _item("Bluetooth Tools", "Eucalyptus WiGLE Upload ON", "eucalyptus_wigle_upload_on", "Arm WiGLE upload without shell exports"),
        _item("Bluetooth Tools", "Eucalyptus WiGLE Upload OFF", "eucalyptus_wigle_upload_off", "Disarm WiGLE upload"),
        _item("Bluetooth Tools", "Eucalyptus Canopy Status", "eucalyptus status", "Show passive BLE, GPS, and WiGLE readiness"),
        _item("Bluetooth Tools", "Eucalyptus Canopy Start", "eucalyptus start", "Start or record passive logging"),
        _item("Bluetooth Tools", "Eucalyptus Canopy Stop", "eucalyptus stop", "Stop or record passive logging"),
        _item("Bluetooth Tools", "Eucalyptus Canopy Restart", "eucalyptus restart", "Restart or record passive logging"),
        _item("Bluetooth Tools", "Eucalyptus GPS Trail", "eucalyptus gps-trail", "Build a GPS-enriched trail"),
        _item("Bluetooth Tools", "Eucalyptus Upload Trail", "eucalyptus upload-status", "Show upload readiness"),
        _item("Bluetooth Tools", "Eucalyptus WiGLE Upload", "eucalyptus wigle-upload", "Upload or dry-run according to menu prompt state"),
        _item("Bluetooth Tools", "Eucalyptus Koalagotchi Mode", "eucalyptus_mode", "Open the Koalagotchi Bluetooth screen"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "kruisin": [
        _item("Bluetooth Tools", "Kruisin’ Prompt Status", "kruisin_prompt_status", "Show saved survey/GPS/node/WiGLE prompt state"),
        _item("Bluetooth Tools", "Kruisin’ GPS ON", "kruisin_gps_on", "Enable survey GPS enrichment from the menu"),
        _item("Bluetooth Tools", "Kruisin’ GPS OFF", "kruisin_gps_off", "Disable survey GPS enrichment"),
        _item("Bluetooth Tools", "Kruisin’ Nodes ON", "kruisin_nodes_on", "Enable ESP32/Heltec node collection"),
        _item("Bluetooth Tools", "Kruisin’ Nodes OFF", "kruisin_nodes_off", "Disable ESP32/Heltec node collection"),
        _item("Bluetooth Tools", "Kruisin’ Default Ports", "kruisin_default_ports", "Use /dev/ttyACM1 for ESP32 and /dev/ttyACM0 for Heltec"),
        _item("Bluetooth Tools", "Kruisin’ WiGLE Dry-Run ON", "kruisin_wigle_dry_run_on", "Build WiGLE CSV without uploading"),
        _item("Bluetooth Tools", "Kruisin’ WiGLE Dry-Run OFF", "kruisin_wigle_dry_run_off", "Allow real upload when armed and credentials exist"),
        _item("Bluetooth Tools", "Kruisin’ WiGLE Upload ON", "kruisin_wigle_upload_on", "Arm WiGLE upload without shell exports"),
        _item("Bluetooth Tools", "Kruisin’ WiGLE Upload OFF", "kruisin_wigle_upload_off", "Disarm WiGLE upload"),
        _item("Bluetooth Tools", "Kruisin’ Status", "kruisin status", "Show survey readiness"),
        _item("Bluetooth Tools", "Wi-Fi AP Survey", "kruisin wifi-survey", "Run passive Wi-Fi AP survey"),
        _item("Bluetooth Tools", "BLE Survey", "kruisin ble-survey", "Run passive BLE survey"),
        _item("Bluetooth Tools", "Wi-Fi + BLE Survey", "kruisin survey", "Run combined survey and write mapping artifacts"),
        _item("Didgeridoo", "Kruisin’ GPS Status", "kruisin gps-status", "Show GPS readiness for mapping"),
        _item("Reports & Reviews", "Kruisin’ WiGLE Upload", "kruisin wigle-upload", "Upload or dry-run according to menu prompt state"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "bluetooth": [
        _item("Bluetooth Tools", "Koala Kapture", "koala_kapture", "Record authorized lab observation metadata"),
        _item("Bluetooth Tools", "Koala Kry", "submenu:koala_kry", "Open Koala Kry offline replay and review prompt controls"),
        _item("Bluetooth Tools", "KoalaByte Lab", "ear_tag_tx_lab", "Create an owned-device lab plan"),
        _item("Bluetooth Tools", "Outback Module Deck", "koala_bluez_manifest", "Show the BlueZ module manifest"),
        _item("Bluetooth Tools", "Gumleaf Gear Check", "koala_bluez_inventory", "Inventory local helpers"),
        _item("Bluetooth Tools", "Eucalyptus Bus Scout", "koala_bluez_status", "Collect local adapter status"),
        _item("Bluetooth Tools", "Dropbear Discovery Sweep", "koala_bluez_scan", "Run bounded local discovery"),
        _item("Bluetooth Tools", "Billabong HCI Watch", "koala_bluez_monitor", "Run bounded local monitor capture"),
        _item("Bluetooth Tools", "Kookaburra Safe Nest Run", "koala_bluez_all_safe", "Run inventory, status, and bounded discovery"),
        _item("Bluetooth Tools", "Joey Target Dossier", "koala_bluez_info", "Protected owned-device info card"),
        _item("Bluetooth Tools", "Treehouse Service Trace", "koala_bluez_services", "Protected owned-device service notes"),
        _item("Bluetooth Tools", "Gumnut GATT Gatecheck", "koala_bluez_gatt_readiness", "Protected owned-device checklist"),
        _item("Bluetooth Tools", "Outback Radio Ledger", "bluez_outback_radio_ledger", "Protected local adapter ledger"),
        _item("Bluetooth Tools", "Classic Track Finder", "bluez_classic_track_finder", "Protected classic controller listing"),
        _item("Bluetooth Tools", "Treehouse RFCOMM Wiremap", "bluez_treehouse_rfcomm_wiremap", "Protected RFCOMM status map"),
        _item("Bluetooth Tools", "Pouch Link Echo", "bluez_pouch_link_echo", "Protected owned-device echo check"),
        _item("Bluetooth Tools", "Gumnut GATT Ghostmap", "bluez_gumnut_gatt_ghostmap", "Protected owned-device service map"),
        _item("Bluetooth Tools", "Platypus BT-Proxy", "bluez_platypus_bt_proxy", "Protected readiness check only"),
        _item("Bluetooth Tools", "that’s not a knife", "thats_not_a_knife", "Defensive local BLE pressure guard"),
        _item("Bluetooth Tools", "AntEater", "anteater", "Passive BLE risk triage with redacted reports"),
        _item("Bluetooth Tools", "Urban Poaching", "urban_poaching", "Authorized BLE RSSI lab game"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "koala_kry": [
        _item("Bluetooth Tools", "Kry Prompt Status", "koala_kry_prompt_status", "Show saved Koala Kry replay/review prompt state"),
        _item("Bluetooth Tools", "Use Latest Capture", "koala_kry_use_latest_capture", "Select the newest Koala Kapture file as the replay source"),
        _item("Bluetooth Tools", "Speed Live", "koala_kry_speed_live", "Replay using captured timing at 1x speed"),
        _item("Bluetooth Tools", "Speed Fast", "koala_kry_speed_fast", "Replay metadata at 5x speed"),
        _item("Bluetooth Tools", "Speed Instant", "koala_kry_speed_instant", "Replay metadata as fast as possible"),
        _item("Bluetooth Tools", "Limit 50 Records", "koala_kry_limit_50", "Limit the next replay/review to 50 records"),
        _item("Bluetooth Tools", "Limit 200 Records", "koala_kry_limit_200", "Limit the next replay/review to 200 records"),
        _item("Bluetooth Tools", "Replay All Records", "koala_kry_limit_all", "Clear the record limit for the next replay/review"),
        _item("Bluetooth Tools", "RF Review ON", "koala_kry_rf_review_on", "Add RF bench isolation review artifact; no RF is sent"),
        _item("Bluetooth Tools", "RF Review OFF", "koala_kry_rf_review_off", "Disable RF bench review artifact"),
        _item("Bluetooth Tools", "Lab Ack ON", "koala_kry_lab_ack_on", "Mark the review as an owned/authorized lab setting"),
        _item("Bluetooth Tools", "Owned Device Ack ON", "koala_kry_owned_ack_on", "Mark captures as owned or scope-approved"),
        _item("Bluetooth Tools", "Clear Kry Draft", "koala_kry_clear_prompt", "Reset Koala Kry prompt state to safe defaults"),
        _item("Bluetooth Tools", "Run Koala Kry Replay", "koala_kry_run_replay", "Run offline metadata replay using the saved prompt"),
        _item("Bluetooth Tools", "Write RF Bench Review", "koala_kry_run_review", "Write replay summary plus RF bench review; no RF is sent"),
        _item("System / Companion", "Back to Bluetooth Tools", "submenu:bluetooth", "Return to Bluetooth Tools"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "didgeridoo": [
        _item("Didgeridoo", "Heltec Link", "status:t114_link", "Constant status: connected or disconnected"),
        _item("Didgeridoo", "Radio/GPS", "status:t114_radio_gps", "Constant Heltec BLE and GPS state"),
        _item("Didgeridoo", "T114 BLE Check", "t114_primary_ble_scan", "Run a bounded T114 nRF52840 BLE radio check"),
        _item("Didgeridoo", "Lab TX Status", "status:t114_tx", "Constant safe lab transmit status"),
        _item("Didgeridoo", "Sextant", "t114_primary_gnss_fix", "Get the current GPS/GNSS location"),
        _item("Didgeridoo", "Location Unlock ON", "location_gate_unlock_on", "Unlock protected local location actions from the menu"),
        _item("Didgeridoo", "Location Unlock OFF", "location_gate_unlock_off", "Lock protected local location actions"),
        _item("Didgeridoo", "Meshtastic App", "submenu:meshtastic", "Open Meshtastic phone app, ESP32 node, Heltec serial, BLE, TCP, status, nodes, and GPS helpers"),
        _item("Didgeridoo", "Protected Location Gate Status", "location_gate_status", "Show protected-actions password gate state"),
        _item("Didgeridoo", "Protected GNSS Current Fix", "gnss_current_fix", "Show current GNSS fix when unlocked"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "meshtastic": [
        _item("Didgeridoo", "Meshtastic Profile", "meshtastic_profile", "Show the saved or environment-derived connection profile"),
        _item("Didgeridoo", "Meshtastic Compatibility", "meshtastic_compatibility", "Show iPhone, Android, Heltec, and ESP32 compatibility notes"),
        _item("Didgeridoo", "Phone App Pairing", "meshtastic_phone_pairing", "Show phone app pairing notes"),
        _item("Didgeridoo", "ESP32 Device Link", "meshtastic_esp32_device", "Show serial, TCP, and BLE options for an ESP32 Meshtastic node"),
        _item("Didgeridoo", "Use Heltec USB Serial", "meshtastic_setup_serial", "Save a local Heltec USB serial profile"),
        _item("Didgeridoo", "Use Network TCP", "meshtastic_setup_tcp", "Save a TCP profile when host env is set"),
        _item("Didgeridoo", "Use BLE Link", "meshtastic_setup_ble", "Save a BLE profile or allow CLI selection"),
        _item("Didgeridoo", "Meshtastic Status", "meshtastic_status", "Show local Meshtastic node status"),
        _item("Didgeridoo", "Meshtastic Nodes", "meshtastic_nodes", "Show the Meshtastic node table"),
        _item("Didgeridoo", "Meshtastic GPS Info", "meshtastic_gps", "Show GPS/GNSS status from the connected node"),
        _item("Didgeridoo", "Meshtastic Listen Gate", "meshtastic_listen", "Run protected receive/listen mode only when unlocked"),
        _item("Didgeridoo", "Send Prompt Status", "meshtastic_send_prompt", "Show the menu-managed message and confirmation state"),
        _item("Didgeridoo", "Set Test Message", "meshtastic_set_test_message", "Set message to Test from KoalaByte Blue and turn confirmation off"),
        _item("Didgeridoo", "Set Check-In Message", "meshtastic_set_checkin_message", "Set message to KoalaByte Blue check-in and turn confirmation off"),
        _item("Didgeridoo", "Confirm Send ON", "meshtastic_confirm_send_on", "Arm the saved message for the intentional send path"),
        _item("Didgeridoo", "Confirm Send OFF", "meshtastic_confirm_send_off", "Disarm send confirmation"),
        _item("Didgeridoo", "Clear Send Draft", "meshtastic_clear_send_prompt", "Clear message, destination, channel, and confirmation"),
        _item("Didgeridoo", "Meshtastic Send Gate", "meshtastic_send_gate", "Send the saved message only when confirmation and protected gate are armed"),
        _item("System / Companion", "Back to Didgeridoo", "submenu:didgeridoo", "Return to the Didgeridoo menu"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "can_bench": [
        _item("CAN Bench Tools", "Koala Kan Kommander", "koala_kan_kommander", "Optional InnoMaker USB-to-CAN bench workflow"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "reports": [
        _item("Reports & Reviews", "Koala Kry RF Review", "koala_kry_transmit_review", "Write RF bench review; no RF is sent"),
        _item("Reports & Reviews", "Boomerang", "boomerang", "Camera-awareness logbook"),
        _item("Reports & Reviews", "Authorized BLE Inventory", "authorized_ble_inventory", "Create a lab inventory from local observations"),
        _item("Reports & Reviews", "GATT Readiness Checklist", "gatt_readiness_checklist", "Generate a pre-test checklist"),
        _item("Reports & Reviews", "Pairing Security Review", "pairing_security_review", "Review pairing posture"),
        _item("Reports & Reviews", "Lab Beacon Plan", "lab_beacon_plan", "Create a safe demo beacon plan"),
        _item("Reports & Reviews", "Packet Capture Notes", "packet_capture_notes", "Create protocol-analysis notes"),
        _item("Reports & Reviews", "Defensive Lab Report", "defensive_report", "Generate a defensive lab report template"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "system": [
        _item("System / Companion", "Prompt State Status", "prompt_state_status", "Show all menu-managed prompt toggles"),
        _item("System / Companion", "Koala Mode Switcher", "koala_mode_switcher", "Build/package/select legacy mode helpers"),
        _item("System / Companion", "KillerKoala Voice", "killerkoala_voice", "Preview voice and vocabulary"),
        _item("System / Companion", "Buttons", "buttons", "Show/check GPIO button status"),
        _item("System / Companion", "Level / Status", "level/status", "Show XP and rank"),
        _item("System / Companion", "Wake killerkoala", "wake killerkoala", "Test wake-word flow"),
        _item("System / Companion", "Restricted Placeholder", "restricted_placeholder", "Reserved locked slot", enabled=False),
        _item("System / Companion", "Settings", "settings", "Device and companion settings"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "lab": [
        _item("Bluetooth Tools", "Joey Target Dossier", "koala_bluez_info", "Protected owned-device info card"),
        _item("Bluetooth Tools", "Treehouse Service Trace", "koala_bluez_services", "Protected owned-device service notes"),
        _item("Bluetooth Tools", "Gumnut GATT Gatecheck", "koala_bluez_gatt_readiness", "Protected owned-device checklist"),
        _item("Bluetooth Tools", "Outback Radio Ledger", "bluez_outback_radio_ledger", "Protected local adapter ledger"),
        _item("Bluetooth Tools", "Classic Track Finder", "bluez_classic_track_finder", "Protected controller listing"),
        _item("Bluetooth Tools", "Treehouse RFCOMM Wiremap", "bluez_treehouse_rfcomm_wiremap", "Protected RFCOMM status map"),
        _item("Bluetooth Tools", "Pouch Link Echo", "bluez_pouch_link_echo", "Protected owned-device echo check"),
        _item("Bluetooth Tools", "Gumnut GATT Ghostmap", "bluez_gumnut_gatt_ghostmap", "Protected owned-device service map"),
        _item("Bluetooth Tools", "Platypus BT-Proxy", "bluez_platypus_bt_proxy", "Protected readiness check"),
        _item("Didgeridoo", "Location Unlock ON", "location_gate_unlock_on", "Unlock protected local location actions from the menu"),
        _item("Didgeridoo", "Location Unlock OFF", "location_gate_unlock_off", "Lock protected local location actions"),
        _item("Didgeridoo", "Protected Location Gate Status", "location_gate_status", "Show protected-actions gate state"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
    "power": [
        _item("System / Companion", "Shutdown", "shutdown_confirm", "Confirm safe shutdown"),
        _item("System / Companion", "Quit", "quit", "Exit the Pi companion UI"),
        _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
    ],
}

FUNCTION_MENU_ITEMS = MAIN_MENU_ITEMS


def submenu_name_from_command(command: str) -> str:
    return command.split(":", 1)[1].strip().lower() if command.startswith("submenu:") else ""


def submenu_title(menu_name: str) -> str:
    titles = {"main": "Main Canopy", "eucalyptus": "Eucalyptus", "kruisin": "Koala Kombat Kruisin’", "bluetooth": "Bluetooth Tools", "koala_kry": "Koala Kry", "didgeridoo": "Didgeridoo", "meshtastic": "Meshtastic App", "can_bench": "CAN Bench Tools", "reports": "Reports & Reviews", "system": "System / Companion", "lab": "Authorized Lab", "power": "Power & Exit"}
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
