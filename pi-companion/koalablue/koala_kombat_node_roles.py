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
        role="primary BLE controller plus GNSS and LoRa; it controls the Raspberry Pi BLE node and receives canonical display state from the Pi",
    ),
    "raspberry-pi": KoalaKombatNodeRole(
        node_id="raspberry-pi",
        wifi=True,
        ble=True,
        gnss=False,
        lora=False,
        ble_primary=False,
        role="BLE node/peer for the Heltec T114 controller, main Wi-Fi execution/AI brain, and canonical expression-state coordinator",
    ),
    "esp32-s3-dualeye": KoalaKombatNodeRole(
        node_id="esp32-s3-dualeye",
        wifi=True,
        ble=False,
        gnss=False,
        lora=False,
        ble_primary=False,
        role="Pi-facing Wi-Fi and USB command/telemetry/audio node; BLE is disabled on this hardware profile",
    ),
}


def node_role_manifest() -> dict[str, object]:
    return {
        "primary_ble_controller": "heltec-t114-nrf52840",
        "primary_ble_node": "heltec-t114-nrf52840",
        "heltec_ble_peer": "raspberry-pi",
        "main_wifi_node": "raspberry-pi",
        "expression_state_coordinator": "raspberry-pi",
        "expression_sync_transport": "pi_fanout_to_each_connected_display",
        "expression_sync_requires_esp32_heltec_ble_link": False,
        "wifi_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.wifi],
        "ble_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.ble],
        "ble_support_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.ble and not role.ble_primary],
        "gnss_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.gnss],
        "lora_nodes": [node_id for node_id, role in NODE_ROLES.items() if role.lora],
        "roles": {node_id: asdict(role) for node_id, role in NODE_ROLES.items()},
        "heltec_t114_has_wifi": False,
        "esp32_ble_enabled": False,
        "policy": "The Heltec T114 is the primary BLE controller and the Raspberry Pi is its BLE node/peer. The Pi remains the canonical execution and expression coordinator and independently sends matching state to the ESP32-S3 DualEye over Wi-Fi or USB and to the Heltec over the Heltec-to-Pi connection. The ESP32-S3 DualEye does not initialize Bluetooth.",
    }


def looks_like_heltec_node(source: str, role: str = "") -> bool:
    haystack = f"{source} {role}".lower()
    return any(token in haystack for token in ("heltec", "t114", "nrf52840", "sx1262"))


def wifi_allowed_for_node(source: str, role: str = "") -> bool:
    if looks_like_heltec_node(source, role):
        return False
    return True
