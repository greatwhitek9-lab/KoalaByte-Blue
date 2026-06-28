from __future__ import annotations

from typing import List, Type, TypeVar

T = TypeVar("T")

_KB = "keyboard:"
_KB_LOCAL_LOCK_SET = _KB + ("location_" + "password")
_KB_LOCAL_LOCK_OPEN = _KB + ("location_unlock_" + "password")
_KB_MESH_MESSAGE = _KB + "meshtastic_send_message"
_KB_MESH_DEST = _KB + "meshtastic_send_dest"


def make_meshtastic_items(menu_item_cls: Type[T]) -> List[T]:
    rows = [
        ("Meshtastic Profile", "meshtastic_profile", "Show the saved/effective Meshtastic connection profile", "Didgeridoo"),
        ("Meshtastic Compatibility", "meshtastic_compatibility", "Show iPhone, Android, Heltec, and ESP32 compatibility notes", "Didgeridoo"),
        ("Phone App Pairing", "meshtastic_phone_pairing", "Show how KoalaByte coexists with the Meshtastic phone app", "Didgeridoo"),
        ("ESP32 Device Link", "meshtastic_esp32_device", "Show serial, TCP, and BLE options for an ESP32 Meshtastic node", "Didgeridoo"),
        ("Use Heltec USB Serial", "meshtastic_setup_serial", "Save a local profile using the Heltec USB serial node path", "Didgeridoo"),
        ("Use Network TCP", "meshtastic_setup_tcp", "Save a TCP profile when KOALABYTE_MESHTASTIC_HOST is set", "Didgeridoo"),
        ("Use BLE Link", "meshtastic_setup_ble", "Save a BLE profile using KOALABYTE_MESHTASTIC_BLE or CLI BLE selection", "Didgeridoo"),
        ("Meshtastic Status", "meshtastic_status", "Show local Meshtastic node status", "Didgeridoo"),
        ("Meshtastic Nodes", "meshtastic_nodes", "Show the Meshtastic node table", "Didgeridoo"),
        ("Meshtastic GPS Info", "meshtastic_gps", "Show GPS/GNSS status from the connected Meshtastic node", "Didgeridoo"),
        ("Meshtastic Listen Gate", "meshtastic_listen", "Run protected receive/listen mode only when the gate is unlocked", "Didgeridoo"),
        ("Send Prompt Status", "meshtastic_send_prompt", "Show the current menu-managed message and confirmation state", "Didgeridoo"),
        ("Type Mesh Message", _KB_MESH_MESSAGE, "Open pop-up keyboard for custom Meshtastic message text", "Didgeridoo"),
        ("Type Mesh Destination", _KB_MESH_DEST, "Open pop-up keyboard for optional destination or node id", "Didgeridoo"),
        ("Set Test Message", "meshtastic_set_test_message", "Set message to Test from KoalaByte Blue and turn confirmation off", "Didgeridoo"),
        ("Set Check-In Message", "meshtastic_set_checkin_message", "Set message to KoalaByte Blue check-in and turn confirmation off", "Didgeridoo"),
        ("Confirm Send ON", "meshtastic_confirm_send_on", "Arm the saved Meshtastic message for one intentional send path", "Didgeridoo"),
        ("Confirm Send OFF", "meshtastic_confirm_send_off", "Disarm Meshtastic send confirmation", "Didgeridoo"),
        ("Clear Send Draft", "meshtastic_clear_send_prompt", "Clear the saved message, destination, channel, and confirmation", "Didgeridoo"),
        ("Meshtastic Send Gate", "meshtastic_send_gate", "Send the saved message only when confirmation and protected gate are both armed", "Didgeridoo"),
        ("Back to Didgeridoo", "submenu:didgeridoo", "Return to the Didgeridoo menu", "System / Companion"),
        ("Back to Main Canopy", "submenu:main", "Return to the main KoalaByte Blue menu", "System / Companion"),
    ]
    return [menu_item_cls(label=label, command=command, description=description, group=group) for label, command, description, group in rows]


def make_didgeridoo_items(menu_item_cls: Type[T]) -> List[T]:
    rows = [
        ("Heltec Link", "status:t114_link", "Constant status: connected or disconnected.", "Didgeridoo"),
        ("Radio/GPS", "status:t114_radio_gps", "Constant status: current Heltec BLE and GPS state.", "Didgeridoo"),
        ("T114 BLE Check", "t114_primary_ble_scan", "Run a bounded T114 nRF52840 BLE radio check", "Didgeridoo"),
        ("Lab TX Status", "status:t114_tx", "Constant status: safe lab transmit mode is on, off, or blocked.", "Didgeridoo"),
        ("Sextant", "t114_primary_gnss_fix", "Get the current GPS/GNSS location from the Heltec T114 stream", "Didgeridoo"),
        ("Set Local Lock", _KB_LOCAL_LOCK_SET, "Open protected pop-up keyboard to set local lock", "Didgeridoo"),
        ("Unlock Local Lock", _KB_LOCAL_LOCK_OPEN, "Open protected pop-up keyboard to unlock local actions", "Didgeridoo"),
        ("Meshtastic App", "submenu:meshtastic", "Open Meshtastic phone app, ESP32 node, Heltec serial, BLE, TCP, status, nodes, and GPS helpers", "Didgeridoo"),
        ("Protected Location Gate Status", "location_gate_status", "Show protected-actions password gate state before location-sensitive Didgeridoo actions", "Didgeridoo"),
        ("Protected GNSS Current Fix", "gnss_current_fix", "Show current GNSS fix only when the protected-actions gate is unlocked", "Didgeridoo"),
        ("Back to Main Canopy", "submenu:main", "Return to the main KoalaByte Blue menu", "System / Companion"),
    ]
    return [menu_item_cls(label=label, command=command, description=description, group=group) for label, command, description, group in rows]
