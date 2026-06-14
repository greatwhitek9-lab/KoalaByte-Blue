"""Authorized Lab Use actions for KoalaByte Blue.

Defensive-only workflows for owned devices, lab hardware, and written-scope
assessments. This module provides safe menu actions and audit logging.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional
import json


class LabActionError(RuntimeError):
    """Raised when an authorized lab action cannot run safely."""


@dataclass(frozen=True)
class LabActionResult:
    action_id: str
    status: str
    message: str
    xp_reward: int = 0
    artifact_path: Optional[str] = None


@dataclass(frozen=True)
class LabAction:
    action_id: str
    title: str
    description: str
    xp_reward: int
    requires_authorization: bool = True
    passive_or_documentation_only: bool = True


class AuthorizedLabActions:
    """Consent-gated defensive lab action registry."""

    def __init__(self, log_dir: str | Path = "logs/lab_actions") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._actions: Dict[str, tuple[LabAction, Callable[[dict], LabActionResult]]] = {}
        self._register_defaults()

    def list_actions(self) -> List[LabAction]:
        return [entry[0] for entry in self._actions.values()]

    def run(self, action_id: str, *, context: Optional[dict] = None, authorized: bool = False) -> LabActionResult:
        if action_id not in self._actions:
            raise LabActionError(f"Unknown lab action: {action_id}")
        action, handler = self._actions[action_id]
        if action.requires_authorization and not authorized:
            result = LabActionResult(
                action_id=action_id,
                status="AUTH_REQUIRED",
                message="Authorization acknowledgement required before running this lab action.",
            )
            self._write_audit(result, {"authorized": False, "context": context or {}})
            return result
        result = handler(context or {})
        self._write_audit(result, {"authorized": authorized, "context": context or {}})
        return result

    def _register(self, action: LabAction, handler: Callable[[dict], LabActionResult]) -> None:
        self._actions[action.action_id] = (action, handler)

    def _register_defaults(self) -> None:
        self._register(LabAction("authorized_ble_inventory", "Authorized BLE inventory", "Create a lab inventory from passive BLE observations.", 10), self._authorized_ble_inventory)
        self._register(LabAction("gatt_readiness_checklist", "GATT readiness checklist", "Generate a pre-test checklist before an owned-device GATT review.", 8), self._gatt_readiness_checklist)
        self._register(LabAction("pairing_security_review", "Pairing security review", "Review expected pairing and access-control posture for owned lab devices.", 8), self._pairing_security_review)
        self._register(LabAction("lab_beacon_plan", "Lab beacon simulation plan", "Create a safe plan for ESP32 demo beacon/peripheral testing.", 10), self._lab_beacon_plan)
        self._register(LabAction("packet_capture_notes", "Packet capture notes", "Create safe Wireshark/nRF52840 notes for owned-device protocol analysis.", 8), self._packet_capture_notes)
        self._register(LabAction("defensive_report", "Defensive lab report", "Generate a defensive report template from current lab context.", 12), self._defensive_report)
        self._register(LabAction("restricted_placeholder", "Restricted placeholder", "Reserved menu slot that remains locked and non-operational.", 0), self._restricted_placeholder)

    def _artifact(self, stem: str, body: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.log_dir / f"{ts}_{stem}.md"
        path.write_text(body, encoding="utf-8")
        return str(path)

    def _authorized_ble_inventory(self, context: dict) -> LabActionResult:
        body = "# Authorized BLE Inventory\n\nScope: owned devices, lab hardware, or written-scope devices only.\n\n"
        devices = context.get("devices", [])
        if devices:
            body += "| Name | Address | RSSI | Connectable | Notes |\n|---|---|---:|---|---|\n"
            for d in devices:
                body += f"| {d.get('name','')} | {d.get('address', d.get('addr',''))} | {d.get('rssi','')} | {d.get('connectable','')} | passive observation |\n"
        else:
            body += "No device list was supplied. Run a passive scan first, then re-run this action.\n"
        artifact = self._artifact("authorized_ble_inventory", body)
        return LabActionResult("authorized_ble_inventory", "OK", "Inventory report generated. killerkoala tagged the lab ghosts.", 10, artifact)

    def _gatt_readiness_checklist(self, context: dict) -> LabActionResult:
        body = "# GATT Readiness Checklist\n\n"
        body += "- [ ] Device is owned by you or covered by written scope.\n"
        body += "- [ ] Device is in an isolated lab or approved assessment area.\n"
        body += "- [ ] Expected services and characteristics are documented.\n"
        body += "- [ ] Read/write tests are limited to non-destructive demo characteristics.\n"
        body += "- [ ] Logs are stored only for the approved engagement.\n"
        artifact = self._artifact("gatt_readiness_checklist", body)
        return LabActionResult("gatt_readiness_checklist", "OK", "Checklist forged. Clean lab work only.", 8, artifact)

    def _pairing_security_review(self, context: dict) -> LabActionResult:
        body = "# Pairing Security Review\n\n"
        body += "Recommended owned-device checks:\n\n"
        body += "- Prefer authenticated pairing for sensitive controls.\n"
        body += "- Require encrypted access for writable characteristics.\n"
        body += "- Minimize identifying data in advertisements.\n"
        body += "- Validate address privacy behavior for portable devices.\n"
        body += "- Confirm expected bond reset and re-pairing behavior.\n"
        artifact = self._artifact("pairing_security_review", body)
        return LabActionResult("pairing_security_review", "OK", "Pairing review generated. Weak links marked in neon.", 8, artifact)

    def _lab_beacon_plan(self, context: dict) -> LabActionResult:
        body = "# Lab Beacon Simulation Plan\n\n"
        body += "Safe ESP32 lab modes:\n\n"
        body += "1. KoalaByte demo beacon with a clearly labeled lab UUID.\n"
        body += "2. Fake battery service for mobile-app testing.\n"
        body += "3. Fake temperature sensor with non-sensitive demo data.\n"
        body += "4. Notification counter characteristic for client UI testing.\n"
        body += "5. Secure-vs-open demo profile using only your own test clients.\n"
        artifact = self._artifact("lab_beacon_plan", body)
        return LabActionResult("lab_beacon_plan", "OK", "Beacon plan staged. Neon bait, lab-only bite.", 10, artifact)

    def _packet_capture_notes(self, context: dict) -> LabActionResult:
        body = "# Authorized Packet Capture Notes\n\n"
        body += "Use the Nordic nRF52840 Dongle only for owned/lab traffic or written-scope work.\n\n"
        body += "Workflow:\n\n"
        body += "1. Confirm scope and device IDs.\n"
        body += "2. Start Wireshark/nRF Sniffer capture.\n"
        body += "3. Generate benign lab traffic from the test peripheral/client.\n"
        body += "4. Annotate timestamps and expected operations.\n"
        body += "5. Export PCAP and include it in the lab report.\n"
        artifact = self._artifact("packet_capture_notes", body)
        return LabActionResult("packet_capture_notes", "OK", "Capture notes logged. Watch the packets, keep it clean.", 8, artifact)

    def _defensive_report(self, context: dict) -> LabActionResult:
        body = "# KoalaByte Blue Defensive Lab Report\n\n"
        body += f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
        body += "## Scope\n\nOwned devices / written-scope lab devices only.\n\n"
        body += "## Actions Completed\n\n- Passive BLE observation\n- Inventory/risk review\n- Documentation artifact generation\n\n"
        body += "## Safety Notes\n\nOnly defensive or documentation actions were run. Restricted slots remain locked.\n"
        artifact = self._artifact("defensive_lab_report", body)
        return LabActionResult("defensive_report", "OK", "Report printed. Clean receipts for the cyber den.", 12, artifact)

    def _restricted_placeholder(self, context: dict) -> LabActionResult:
        return LabActionResult("restricted_placeholder", "LOCKED", "This menu slot is reserved and intentionally non-operational.", 0, None)

    def _write_audit(self, result: LabActionResult, meta: dict) -> None:
        audit_path = self.log_dir / "authorized_lab_actions.jsonl"
        event = {"timestamp": datetime.now(timezone.utc).isoformat(), "result": asdict(result), "meta": meta}
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")


if __name__ == "__main__":
    lab = AuthorizedLabActions()
    print("Authorized Lab Use actions:")
    for action in lab.list_actions():
        print(f"- {action.action_id}: {action.title}")
