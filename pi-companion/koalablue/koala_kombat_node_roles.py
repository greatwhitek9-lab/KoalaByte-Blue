from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class KoalaKombatNodeRole:
    node_id: str
    wifi: bool
    ble: bool
    gnss: bool
    lora: bool
    ble_primary: bool
    role: str


NODE_ROLES = {
    "heltec-t114-nrf52840": KoalaKombatNodeRole(
        node_id="heltec-t114-nrf52840",
        wifi=False,
        ble=True,
        gnss=True,
        lora=True,
        ble_primary=True,
        role="primary BLE board plus GNSS and LoRa; not a Wi-Fi node",
    ),
    "raspberry-pi": KoalaKombatNodeRole(
        node_id="raspberry-pi",
        wifi=True,
        ble=True,
        gnss=False,
        lora=False,
        ble_primary=False,
        role="main Wi-Fi board and BLE support node",
    ),
    "esp32-s3-dualeye": KoalaKombatNodeRole(
        node_id="esp32-s3-dualeye",
        wifi=True,
        ble=True,
        gnss=False,
        lora=False,
        ble_primary=False,
        role="Wi-Fi survey node and BLE support node",
    ),
}


def node_role_manifest() -> dict[str, object]:
    return {
        "primary_ble_node": "heltec-t114-nrf52840",
        "main_wifi_node": "raspberry-pi",
        "wifi_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.wifi],
        "ble_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.ble],
        "ble_support_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.ble and not role.ble_primary],
        "gnss_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.gnss],
        "lora_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.lora],
        "roles": {node_id: asdict(role) for node_id, role in NODE_ROLES.items()},
        "heltec_t114_has_wifi": False,
        "policy": "Koala Kombat Kruisin uses the nRF52840 on the Heltec T114 as the primary BLE node, the Pi and ESP32-S3 DualEye as BLE support nodes, the Pi as the main Wi-Fi node, and the ESP32-S3 DualEye as the only extra Wi-Fi survey node. The Heltec T114 is BLE/GNSS/LoRa only.",
    }


def looks_like_heltec_node(source: str, role: str = "") -> bool:
    haystack = f"{source} {role}".lower()
    return any(token in haystack for token in ("heltec", "t114", "nrf52840", "sx1262"))


def wifi_allowed_for_node(source: str, role: str = "") -> bool:
    if looks_like_heltec_node(source, role):
        return False
    return True
