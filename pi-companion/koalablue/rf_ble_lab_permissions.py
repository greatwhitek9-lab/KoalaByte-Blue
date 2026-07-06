from __future__ import annotations

from copy import deepcopy
from typing import Any

RF_BLE_LAB_PERMISSIONS: dict[str, Any] = {
    "rf_ble_live_transmit": True,
    "synthetic_lab_transmit": True,
    "saved_signal_replay": True,
    "saved_signal_replay_scope": "offline_saved_artifact_replay",
    "captured_metadata_replay": True,
    "captured_signal_replay": False,
    "over_air_signal_replay": False,
}


def permission_manifest() -> dict[str, Any]:
    """Return the canonical Koala Kry/Kapture RF/BLE lab permission state.

    `saved_signal_replay` means replay from saved local artifacts for UI,
    reporting, parsing, and lab workflow validation. It does not mean over-air
    rebroadcast of captured RF/BLE signals.
    """

    return deepcopy(RF_BLE_LAB_PERMISSIONS)
