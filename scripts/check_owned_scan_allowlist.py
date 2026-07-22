#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.owned_scan_allowlist import (  # noqa: E402
    clear_owned_scan_identity_cache,
    is_owned_scan_observation,
    owned_scan_identity,
    owned_scan_reason,
)


def main() -> int:
    previous_names = os.environ.get("KOALABYTE_OWNED_SCAN_NAMES")
    previous_addresses = os.environ.get("KOALABYTE_OWNED_SCAN_ADDRESSES")
    previous_override = os.environ.get("KOALABYTE_INCLUDE_OWNED_SCAN_NODES")
    try:
        os.environ["KOALABYTE_OWNED_SCAN_NAMES"] = "Custom-Koala-Pi"
        os.environ["KOALABYTE_OWNED_SCAN_ADDRESSES"] = "02:11:22:33:44:55"
        os.environ.pop("KOALABYTE_INCLUDE_OWNED_SCAN_NODES", None)
        clear_owned_scan_identity_cache()

        checks = {
            "esp32_name": is_owned_scan_observation(name="KoalaBlue-DualEye"),
            "esp32_suffix_name": is_owned_scan_observation(name="KoalaBlue-DualEye-01"),
            "heltec_name": is_owned_scan_observation(name="Heltec T114"),
            "heltec_lab_beacon": is_owned_scan_observation(name="KoalaByte Lab"),
            "pi_hostname": is_owned_scan_observation(name=socket.gethostname()),
            "custom_name": is_owned_scan_observation(name="Custom Koala Pi"),
            "custom_address": is_owned_scan_observation(address="02-11-22-33-44-55"),
            "external_device_kept": not is_owned_scan_observation(
                name="Neighbour Sensor", address="AA:BB:CC:DD:EE:FF"
            ),
            "scanner_source_not_misclassified": not is_owned_scan_observation(
                {
                    "source": "heltec-t114-nrf52840",
                    "name": "Neighbour Sensor",
                    "addr": "AA:BB:CC:DD:EE:FF",
                }
            ),
        }
        os.environ["KOALABYTE_INCLUDE_OWNED_SCAN_NODES"] = "1"
        checks["explicit_maintenance_override"] = not is_owned_scan_observation(
            name="KoalaBlue-DualEye"
        )

        failures = sorted(name for name, passed in checks.items() if not passed)
        identity = owned_scan_identity()
        payload = {
            "status": "OWNED_SCAN_ALLOWLIST_READY" if not failures else "OWNED_SCAN_ALLOWLIST_FAILED",
            "checks": checks,
            "failures": failures,
            "owned_name_count": len(identity.names),
            "owned_address_count": len(identity.addresses),
            "identity_sources": identity.sources,
            "sample_reason": owned_scan_reason(name="KoalaBlue-DualEye"),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if failures else 0
    finally:
        if previous_names is None:
            os.environ.pop("KOALABYTE_OWNED_SCAN_NAMES", None)
        else:
            os.environ["KOALABYTE_OWNED_SCAN_NAMES"] = previous_names
        if previous_addresses is None:
            os.environ.pop("KOALABYTE_OWNED_SCAN_ADDRESSES", None)
        else:
            os.environ["KOALABYTE_OWNED_SCAN_ADDRESSES"] = previous_addresses
        if previous_override is None:
            os.environ.pop("KOALABYTE_INCLUDE_OWNED_SCAN_NODES", None)
        else:
            os.environ["KOALABYTE_INCLUDE_OWNED_SCAN_NODES"] = previous_override
        clear_owned_scan_identity_cache()


if __name__ == "__main__":
    raise SystemExit(main())
