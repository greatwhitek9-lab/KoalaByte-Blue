from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CONFIG_PATH = Path(
    os.getenv(
        "KOALABYTE_OWNED_SCAN_ALLOWLIST_FILE",
        "/etc/koalabyte-blue/owned_scan_allowlist.json",
    )
)

# These are KoalaByte-owned controller identities, not arbitrary nearby devices.
# General discovery, logging, alerting, and export paths exclude them by default.
BUILTIN_OWNED_NAMES = {
    "koalablue dualeye",
    "koalabyte dualeye",
    "esp32 s3 dualeye",
    "esp32 dualeye",
    "killerkoala dualeye",
    "koalabyte heltec",
    "koalabyte t114",
    "heltec t114",
    "heltec wireless tracker",
    "koalabyte lab",
}

_ADDRESS_RE = re.compile(r"^[0-9A-F]{12}$")
_SPLIT_RE = re.compile(r"[,;\n]+")
_NAME_CLEAN_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class OwnedScanIdentity:
    names: frozenset[str]
    addresses: frozenset[str]
    sources: tuple[str, ...]


def _truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def normalize_name(value: Any) -> str:
    return " ".join(
        part for part in _NAME_CLEAN_RE.sub(" ", str(value or "").lower()).split() if part
    )


def normalize_address(value: Any) -> str:
    compact = re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()
    if not _ADDRESS_RE.fullmatch(compact):
        return ""
    return ":".join(compact[index : index + 2] for index in range(0, 12, 2))


def _split_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in _SPLIT_RE.split(value) if item.strip()]


def _read_json_config(path: Path) -> tuple[list[str], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [], []
    if not isinstance(payload, dict):
        return [], []
    raw_names = payload.get("names", [])
    raw_addresses = payload.get("addresses", [])
    names = [str(item) for item in raw_names] if isinstance(raw_names, list) else []
    addresses = (
        [str(item) for item in raw_addresses]
        if isinstance(raw_addresses, list)
        else []
    )
    return names, addresses


def _local_interface_addresses() -> list[str]:
    addresses: list[str] = []
    for path in sorted(Path("/sys/class/net").glob("*/address")):
        try:
            address = normalize_address(path.read_text(encoding="utf-8").strip())
        except OSError:
            continue
        if address and address != "00:00:00:00:00:00":
            addresses.append(address)
    return addresses


def _local_bluetooth_identity() -> tuple[list[str], list[str]]:
    names: list[str] = []
    addresses: list[str] = []
    try:
        result = subprocess.run(
            ["bluetoothctl", "show"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return names, addresses
    for raw in (result.stdout or "").splitlines():
        line = raw.strip()
        if line.startswith("Controller "):
            parts = line.split()
            if len(parts) >= 2:
                address = normalize_address(parts[1])
                if address:
                    addresses.append(address)
        elif line.startswith("Name:") or line.startswith("Alias:"):
            value = line.split(":", 1)[1].strip()
            if value:
                names.append(value)
    return names, addresses


@lru_cache(maxsize=1)
def owned_scan_identity() -> OwnedScanIdentity:
    names = set(BUILTIN_OWNED_NAMES)
    addresses: set[str] = set()
    sources = ["builtin-koalabyte-controller-names"]

    hostname = normalize_name(socket.gethostname())
    if hostname:
        names.add(hostname)
        sources.append("local-hostname")

    for value in _split_values(os.getenv("KOALABYTE_OWNED_SCAN_NAMES")):
        normalized = normalize_name(value)
        if normalized:
            names.add(normalized)
    if os.getenv("KOALABYTE_OWNED_SCAN_NAMES"):
        sources.append("environment-names")

    address_envs = (
        "KOALABYTE_OWNED_SCAN_ADDRESSES",
        "KOALABYTE_PI_BLE_ADDRESS",
        "KOALABYTE_PI_WIFI_ADDRESS",
        "KOALABYTE_ESP32_BLE_ADDRESS",
        "KOALABYTE_ESP32_WIFI_ADDRESS",
        "KOALABYTE_HELTEC_BLE_ADDRESS",
    )
    for env_name in address_envs:
        for value in _split_values(os.getenv(env_name)):
            normalized = normalize_address(value)
            if normalized:
                addresses.add(normalized)
    if any(os.getenv(name) for name in address_envs):
        sources.append("environment-addresses")

    config_names, config_addresses = _read_json_config(DEFAULT_CONFIG_PATH)
    for value in config_names:
        normalized = normalize_name(value)
        if normalized:
            names.add(normalized)
    for value in config_addresses:
        normalized = normalize_address(value)
        if normalized:
            addresses.add(normalized)
    if config_names or config_addresses:
        sources.append(str(DEFAULT_CONFIG_PATH))

    local_addresses = _local_interface_addresses()
    addresses.update(local_addresses)
    if local_addresses:
        sources.append("local-network-interfaces")

    bluetooth_names, bluetooth_addresses = _local_bluetooth_identity()
    names.update(normalize_name(value) for value in bluetooth_names if normalize_name(value))
    addresses.update(bluetooth_addresses)
    if bluetooth_names or bluetooth_addresses:
        sources.append("local-bluez-controller")

    return OwnedScanIdentity(
        names=frozenset(names),
        addresses=frozenset(addresses),
        sources=tuple(dict.fromkeys(sources)),
    )


def clear_owned_scan_identity_cache() -> None:
    owned_scan_identity.cache_clear()


def owned_scan_reason(
    payload: dict[str, Any] | None = None,
    *,
    name: Any = "",
    address: Any = "",
    ssid: Any = "",
    bssid: Any = "",
) -> str:
    if _truthy("KOALABYTE_INCLUDE_OWNED_SCAN_NODES"):
        return ""

    data = payload or {}
    identity = owned_scan_identity()
    candidate_addresses = (
        address,
        bssid,
        data.get("addr"),
        data.get("address"),
        data.get("mac"),
        data.get("bssid"),
        data.get("identifier"),
    )
    for value in candidate_addresses:
        normalized = normalize_address(value)
        if normalized and normalized in identity.addresses:
            return f"owned_address:{normalized}"

    candidate_names = (
        name,
        ssid,
        data.get("name"),
        data.get("local_name"),
        data.get("ssid"),
        data.get("advertised_name"),
        data.get("hostname"),
    )
    for value in candidate_names:
        normalized = normalize_name(value)
        if not normalized:
            continue
        for owned in identity.names:
            if normalized == owned or normalized.startswith(f"{owned} "):
                return f"owned_name:{owned}"
    return ""


def is_owned_scan_observation(
    payload: dict[str, Any] | None = None,
    **identity_fields: Any,
) -> bool:
    return bool(owned_scan_reason(payload, **identity_fields))


def filter_owned_scan_observations(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for row in rows:
        reason = owned_scan_reason(row)
        if reason:
            excluded.append(
                {
                    "reason": reason,
                    "name": str(row.get("name") or row.get("local_name") or ""),
                    "address": normalize_address(
                        row.get("addr")
                        or row.get("address")
                        or row.get("mac")
                        or row.get("bssid")
                    ),
                }
            )
        else:
            kept.append(row)
    return kept, excluded
