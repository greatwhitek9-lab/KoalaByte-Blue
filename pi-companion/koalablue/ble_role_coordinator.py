from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_STATUS_PATH = Path("logs/ble_nodes/ble_role_election.json")


@dataclass(frozen=True)
class PiBluezProbe:
    available: bool
    reason: str
    adapter: str = ""
    powered: bool | None = None
    checked_at: float = 0.0


@dataclass(frozen=True)
class BleRoleElection:
    heltec_role: str
    pi_bluez_role: str
    esp32_role: str
    pi_probe: PiBluezProbe
    requested_by: str
    checked_at: float

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["type"] = "ble_role_election"
        payload["heltec_primary"] = True
        payload["single_fallback_owner"] = True
        return payload


def _run(command: list[str], timeout: float = 3.0) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None


def _environment_disabled() -> bool:
    value = os.getenv("KOALABYTE_PI_BLUEZ_NODE", "1").strip().lower()
    return value in {"0", "false", "no", "off", "disabled"}


def _rfkill_blocked() -> bool:
    if not shutil.which("rfkill"):
        return False
    result = _run(["rfkill", "list", "bluetooth"])
    if result is None:
        return False
    text = f"{result.stdout}\n{result.stderr}".lower()
    return "soft blocked: yes" in text or "hard blocked: yes" in text


def probe_pi_bluez() -> PiBluezProbe:
    checked_at = time.time()
    if _environment_disabled():
        return PiBluezProbe(False, "disabled_by_KOALABYTE_PI_BLUEZ_NODE", checked_at=checked_at)
    if _rfkill_blocked():
        return PiBluezProbe(False, "bluetooth_adapter_rfkill_blocked", checked_at=checked_at)

    bluetoothctl = shutil.which("bluetoothctl")
    if bluetoothctl:
        listed = _run([bluetoothctl, "list"])
        if listed is not None:
            for line in listed.stdout.splitlines():
                line = line.strip()
                if line.startswith("Controller "):
                    parts = line.split()
                    adapter = parts[1] if len(parts) > 1 else "hci0"
                    shown = _run([bluetoothctl, "show", adapter])
                    powered: bool | None = None
                    if shown is not None:
                        lower = shown.stdout.lower()
                        if "powered: yes" in lower:
                            powered = True
                        elif "powered: no" in lower:
                            powered = False
                    if powered is False:
                        return PiBluezProbe(False, "bluez_controller_powered_off", adapter, False, checked_at)
                    return PiBluezProbe(True, "bluez_controller_available", adapter, powered, checked_at)

    sysfs = sorted(glob.glob("/sys/class/bluetooth/hci*"))
    if sysfs:
        return PiBluezProbe(True, "bluetooth_sysfs_adapter_available", Path(sysfs[0]).name, None, checked_at)

    return PiBluezProbe(False, "no_pi_bluez_adapter_detected", checked_at=checked_at)


def elect_ble_roles(requested_by: str = "raspberry-pi") -> BleRoleElection:
    probe = probe_pi_bluez()
    return BleRoleElection(
        heltec_role="primary_ble_controller",
        pi_bluez_role="heltec_ble_node" if probe.available else "unavailable",
        esp32_role="standby" if probe.available else "heltec_fallback_ble_node",
        pi_probe=probe,
        requested_by=requested_by,
        checked_at=time.time(),
    )


def esp32_role_command(election: BleRoleElection) -> dict[str, Any]:
    return {
        "type": "ble_role",
        "role": election.esp32_role,
        "reason": election.pi_probe.reason,
        "heltec_primary": True,
        "pi_bluez_available": election.pi_probe.available,
        "requested_by": election.requested_by,
    }


def write_role_status(
    election: BleRoleElection,
    path: str | Path = DEFAULT_STATUS_PATH,
) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(election.to_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return str(target)
