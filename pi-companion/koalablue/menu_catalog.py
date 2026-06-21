from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Type, TypeVar

T = TypeVar("T")

MENU_GROUPS: List[str] = [
    "Bluetooth Tools",
    "CAN Bench Tools",
    "Reports & Reviews",
    "System / Companion",
]

_GROUP_ORDER = {name: index for index, name in enumerate(MENU_GROUPS)}

FUNCTION_MENU_ITEMS: List[dict[str, object]] = [
    {"group": "Bluetooth Tools", "label": "Scan", "command": "scan", "description": "Run a safe local BLE inventory scan"},
    {"group": "Bluetooth Tools", "label": "Summary", "command": "summary", "description": "Summarize observed local BLE devices"},
    {"group": "Bluetooth Tools", "label": "Show Devices", "command": "show", "description": "Show the current local BLE device table"},
    {"group": "Bluetooth Tools", "label": "eucalyptus Status", "command": "eucalyptus status", "description": "Show always-on passive BLE logger status"},
    {"group": "Bluetooth Tools", "label": "eucalyptus Start", "command": "eucalyptus start", "description": "Start always-on passive BLE logging"},
    {"group": "Bluetooth Tools", "label": "eucalyptus Stop", "command": "eucalyptus stop", "description": "Stop always-on passive BLE logging"},
    {"group": "Bluetooth Tools", "label": "eucalyptus Restart", "command": "eucalyptus restart", "description": "Restart always-on passive BLE logging"},
    {"group": "Bluetooth Tools", "label": "eucalyptus Upload Status", "command": "eucalyptus upload-status", "description": "Show upload readiness/status"},
    {"group": "Bluetooth Tools", "label": "Eucalyptus Mode", "command": "eucalyptus_mode", "description": "Koalagotchi always-on Bluetooth scanner and logger screen; stays open until quit"},
    {"group": "Bluetooth Tools", "label": "Koala Kapture", "command": "koala_kapture", "description": "Record authorized lab observation metadata"},
    {"group": "Bluetooth Tools", "label": "Koala Kry", "command": "koala_kry", "description": "Replay local saved metadata into the report pipeline"},
    {"group": "Reports & Reviews", "label": "Koala Kry RF Review", "command": "koala_kry_transmit_review", "description": "Write RF bench isolation and authorization review; no RF is sent"},
    {"group": "Bluetooth Tools", "label": "Ear Tag", "command": "ear_tag", "description": "Named lab BLE beacon"},
    {"group": "Bluetooth Tools", "label": "KoalaByte Lab", "command": "ear_tag_tx_lab", "description": "Synthetic owned-device BLE lab advertisement"},
    {"group": "System / Companion", "label": "Koala Mode Switcher", "command": "koala_mode_switcher", "description": "Build/package/select KoalaByte Lab or Koala Konnect for the nRF52840 Dongle"},
    {"group": "CAN Bench Tools", "label": "Koala Kan Kommander", "command": "koala_kan_kommander", "description": "InnoMaker USB-to-CAN listen and gated bench-simulator transmit plug-in"},
    {"group": "Bluetooth Tools", "label": "Gumleaf Gear Check", "command": "koala_bluez_inventory", "description": "Inventory local BlueZ helpers"},
    {"group": "Bluetooth Tools", "label": "Eucalyptus Bus Scout", "command": "koala_bluez_status", "description": "Collect local adapter and controller status"},
    {"group": "Bluetooth Tools", "label": "Dropbear Discovery Sweep", "command": "koala_bluez_scan", "description": "Run bounded local discovery with safe defaults"},
    {"group": "Bluetooth Tools", "label": "Billabong HCI Watch", "command": "koala_bluez_monitor", "description": "Run bounded local HCI capture"},
    {"group": "Bluetooth Tools", "label": "Kookaburra Safe Nest Run", "command": "koala_bluez_all_safe", "description": "Run local inventory, status, and bounded discovery"},
    {"group": "Bluetooth Tools", "label": "that’s not a knife", "command": "thats_not_a_knife", "description": "that’s not a knife defensive local BLE pressure guard"},
    {"group": "Bluetooth Tools", "label": "AntEater", "command": "anteater", "description": "Passive BLE payment-terminal risk triage with redacted reports"},
    {"group": "System / Companion", "label": "KillerKoala Voice", "command": "killerkoala_voice", "description": "Preview event reactions and vocabulary by XP rank"},
    {"group": "Bluetooth Tools", "label": "Urban Poaching", "command": "urban_poaching", "description": "Authorized BLE RSSI lab game"},
    {"group": "System / Companion", "label": "Buttons", "command": "buttons", "description": "Show/check GPIO front-panel button status"},
    {"group": "System / Companion", "label": "Level / Status", "command": "level/status", "description": "Show XP and rank"},
    {"group": "Reports & Reviews", "label": "Report", "command": "report", "description": "Write a Markdown session report"},
    {"group": "Reports & Reviews", "label": "Boomerang", "command": "boomerang", "description": "Boomerang camera-awareness logbook; manual public observations; stays open until quit"},
    {"group": "System / Companion", "label": "Wake killerkoala", "command": "wake killerkoala", "description": "Test wake-word flow"},
    {"group": "Reports & Reviews", "label": "Authorized BLE Inventory", "command": "authorized_ble_inventory", "description": "Create a lab inventory from local observations"},
    {"group": "Reports & Reviews", "label": "GATT Readiness Checklist", "command": "gatt_readiness_checklist", "description": "Generate a pre-test checklist for owned-device GATT review"},
    {"group": "Reports & Reviews", "label": "Pairing Security Review", "command": "pairing_security_review", "description": "Review owned-device pairing/access-control posture"},
    {"group": "Reports & Reviews", "label": "Lab Beacon Plan", "command": "lab_beacon_plan", "description": "Create a safe ESP32 demo beacon/peripheral testing plan"},
    {"group": "Reports & Reviews", "label": "Packet Capture Notes", "command": "packet_capture_notes", "description": "Create protocol-analysis notes"},
    {"group": "Reports & Reviews", "label": "Defensive Lab Report", "command": "defensive_report", "description": "Generate a defensive lab report template"},
    {"group": "System / Companion", "label": "Restricted Placeholder", "command": "restricted_placeholder", "description": "Reserved locked slot; intentionally non-operational", "enabled": False},
    {"group": "System / Companion", "label": "Settings", "command": "settings", "description": "Device and companion settings"},
    {"group": "System / Companion", "label": "Lab", "command": "lab", "description": "Password-gated Authorized Lab Use menu"},
    {"group": "System / Companion", "label": "Shutdown", "command": "shutdown_confirm", "description": "Confirm safe shutdown"},
    {"group": "System / Companion", "label": "Quit", "command": "quit", "description": "Exit the Pi companion UI"},
]


def _entry_group(entry: dict[str, object]) -> str:
    group = str(entry.get("group", "System / Companion"))
    return group if group in _GROUP_ORDER else "System / Companion"


def grouped_entries() -> Dict[str, List[dict[str, object]]]:
    groups: Dict[str, List[dict[str, object]]] = OrderedDict((name, []) for name in MENU_GROUPS)
    for entry in FUNCTION_MENU_ITEMS:
        groups[_entry_group(entry)].append(entry)
    return groups


def sorted_menu_entries() -> List[dict[str, object]]:
    indexed = list(enumerate(FUNCTION_MENU_ITEMS))
    indexed.sort(key=lambda pair: (_GROUP_ORDER[_entry_group(pair[1])], pair[0]))
    return [entry for _idx, entry in indexed]


def make_menu_items(menu_item_cls: Type[T]) -> List[T]:
    items: List[T] = []
    for entry in sorted_menu_entries():
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


def menu_labels() -> List[str]:
    return [str(item["label"]) for item in FUNCTION_MENU_ITEMS]


def grouped_menu_labels() -> Dict[str, List[str]]:
    return {group: [str(item["label"]) for item in entries] for group, entries in grouped_entries().items()}
