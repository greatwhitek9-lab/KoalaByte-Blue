from __future__ import annotations

from typing import List, Type, TypeVar

T = TypeVar("T")

# One shared source of truth for every safe/local KoalaByte Blue UI action.
# Command strings intentionally match the Pi companion CLI/action vocabulary where it exists.
FUNCTION_MENU_ITEMS: List[dict[str, object]] = [
    {"label": "Scan", "command": "scan", "description": "Run a safe BLE inventory scan"},
    {"label": "Summary", "command": "summary", "description": "Summarize observed BLE devices"},
    {"label": "Show Devices", "command": "show", "description": "Show the current BLE device table"},
    {"label": "eucalyptus Status", "command": "eucalyptus status", "description": "Show always-on passive BLE logger status"},
    {"label": "eucalyptus Start", "command": "eucalyptus start", "description": "Start always-on passive BLE logging"},
    {"label": "eucalyptus Stop", "command": "eucalyptus stop", "description": "Stop always-on passive BLE logging"},
    {"label": "eucalyptus Restart", "command": "eucalyptus restart", "description": "Restart always-on passive BLE logging"},
    {"label": "eucalyptus Upload Status", "command": "eucalyptus upload-status", "description": "Show WiGLE upload readiness/status"},
    {"label": "Koala Kapture", "command": "koala_kapture", "description": "Capture and archive BLE advertisement metadata"},
    {"label": "Koala Kry", "command": "koala_kry", "description": "Replay captured metadata offline into the report/XP pipeline"},
    {"label": "Koala Kry RF Review", "command": "koala_kry_transmit_review", "description": "Write blocked RF transmit review manifest; no RF is sent"},
    {"label": "Ear Tag", "command": "ear_tag", "description": "Named lab BLE beacon"},
    {"label": "KoalaByte Lab", "command": "ear_tag_tx_lab", "description": "Synthetic owned-device BLE advertisement for signal-integrity observation"},
    {"label": "Koala Mode Switcher", "command": "koala_mode_switcher", "description": "Build/package/select KoalaByte Lab or Koala Konnect for the nRF52840 Dongle"},
    {"label": "Koala Kan Kommander", "command": "koala_kan_kommander", "description": "Optional InnoMaker USB-to-CAN status, passive listen, and report plug-in"},
    {"label": "Gumleaf Gear Check", "command": "koala_bluez_inventory", "description": "Inventory installed BlueZ helpers under KoalaByte themed names"},
    {"label": "Eucalyptus Bus Scout", "command": "koala_bluez_status", "description": "Collect local adapter, controller, rfkill, and optional D-Bus status"},
    {"label": "Dropbear Discovery Sweep", "command": "koala_bluez_scan", "description": "Run bounded Bluetooth discovery and save redacted results by default"},
    {"label": "Billabong HCI Watch", "command": "koala_bluez_monitor", "description": "Run bounded btmon HCI capture and save lab artifacts"},
    {"label": "Kookaburra Safe Nest Run", "command": "koala_bluez_all_safe", "description": "Run BlueZ inventory, status, and bounded discovery with safe defaults"},
    {"label": "KillerKoala Voice", "command": "killerkoala_voice", "description": "Preview event reactions and inquiry vocabulary by XP rank"},
    {"label": "Urban Poaching", "command": "urban_poaching", "description": "Authorized BLE RSSI lab game"},
    {"label": "Buttons", "command": "buttons", "description": "Show/check GPIO front-panel button status"},
    {"label": "Level / Status", "command": "level/status", "description": "Show XP and rank"},
    {"label": "Report", "command": "report", "description": "Write a Markdown session report"},
    {"label": "Wake killerkoala", "command": "wake killerkoala", "description": "Test wake-word flow"},
    {"label": "Authorized BLE Inventory", "command": "authorized_ble_inventory", "description": "Create a lab inventory from passive BLE observations"},
    {"label": "GATT Readiness Checklist", "command": "gatt_readiness_checklist", "description": "Generate a pre-test checklist for owned-device GATT review"},
    {"label": "Pairing Security Review", "command": "pairing_security_review", "description": "Review pairing and access-control posture for owned lab devices"},
    {"label": "Lab Beacon Plan", "command": "lab_beacon_plan", "description": "Create a safe ESP32 demo beacon/peripheral testing plan"},
    {"label": "Packet Capture Notes", "command": "packet_capture_notes", "description": "Create safe Wireshark/nRF52840 protocol-analysis notes"},
    {"label": "Defensive Lab Report", "command": "defensive_report", "description": "Generate a defensive lab report template"},
    {"label": "Restricted Placeholder", "command": "restricted_placeholder", "description": "Reserved locked slot; intentionally non-operational", "enabled": False},
    {"label": "Settings", "command": "settings", "description": "Device and companion settings"},
    {"label": "Lab", "command": "lab", "description": "Password-gated Authorized Lab Use menu"},
    {"label": "Shutdown", "command": "shutdown_confirm", "description": "Confirm safe shutdown"},
    {"label": "Quit", "command": "quit", "description": "Exit the Pi companion UI"},
]


def make_menu_items(menu_item_cls: Type[T]) -> List[T]:
    """Build menu item objects for whichever menu front end imports the catalog."""
    items: List[T] = []
    for entry in FUNCTION_MENU_ITEMS:
        kwargs = {
            "label": str(entry["label"]),
            "command": str(entry["command"]),
            "description": str(entry.get("description", "")),
            "enabled": bool(entry.get("enabled", True)),
        }
        try:
            items.append(menu_item_cls(**kwargs))
        except TypeError:
            kwargs.pop("enabled", None)
            items.append(menu_item_cls(**kwargs))
    return items


def menu_labels() -> List[str]:
    return [str(item["label"]) for item in FUNCTION_MENU_ITEMS]
