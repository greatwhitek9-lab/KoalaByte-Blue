from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class KoalaKombatNodeRole:
    node_id: str
    wifi: bool
    ble: bool
    gnss: bool
    lora: bool
    role: str


NODE_ROLES = {
    "raspberry-pi": KoalaKombatNodeRole(
        node_id="raspberry-pi",
        wifi=True,
        ble=True,
        gnss=False,
        lora=False,
        role="main Wi-Fi controller and main BLE node",
    ),
    "esp32-s3-dualeye": KoalaKombatNodeRole(
        node_id="esp32-s3-dualeye",
        wifi=True,
        ble=True,
        gnss=False,
        lora=False,
        role="only secondary Wi-Fi node and second BLE node",
    ),
    "heltec-t114-nrf52840": KoalaKombatNodeRole(
        node_id="heltec-t114-nrf52840",
        wifi=False,
        ble=True,
        gnss=True,
        lora=True,
        role="BLE, GNSS, and LoRa node only; not a Wi-Fi node",
    ),
}


def node_role_manifest() -> dict[str, object]:
    return {
        "wifi_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.wifi],
        "ble_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.ble],
        "gnss_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.gnss],
        "roles": {node_id: asdict(role) for node_id, role in NODE_ROLES.items()},
        "heltec_t114_has_wifi": False,
        "policy": "Koala Kombat Kruisin uses the Pi as the main Wi-Fi controller and BLE node, the ESP32-S3 DualEye as the only secondary Wi-Fi node and second BLE node, and the Heltec T114 as BLE/GNSS/LoRa only.",
    }


def looks_like_heltec_node(source: str, role: str = "") -> bool:
    haystack = f"{source} {role}".lower()
    return any(token in haystack for token in ("heltec", "t114", "nrf52840", "sx1262"))


def wifi_allowed_for_node(source: str, role: str = "") -> bool:
    if looks_like_heltec_node(source, role):
        return False
    return True
