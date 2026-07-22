from __future__ import annotations

import json
import re
from dataclasses import asdict
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from .owned_scan_allowlist import owned_scan_reason

_MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
_INSTALLED = False


def _filter_bluez_text(text: str) -> tuple[str, int]:
    kept: list[str] = []
    excluded = 0
    trailing_newline = text.endswith("\n")
    for line in text.splitlines():
        match = _MAC_RE.search(line)
        address = match.group(0) if match else ""
        name = line[match.end() :].strip() if match else line.strip()
        reason = owned_scan_reason(name=name, address=address)
        if reason:
            excluded += 1
            continue
        kept.append(line)
    filtered = "\n".join(kept)
    if trailing_newline and filtered:
        filtered += "\n"
    return filtered, excluded


def _install_ble_event_filter() -> None:
    from . import ble_event_log

    if getattr(ble_event_log, "_koalabyte_owned_filter_installed", False):
        return

    original_should_emit = ble_event_log.BleEventDeduper.should_emit
    original_append = ble_event_log.BleEventLog.append

    @wraps(original_should_emit)
    def should_emit(self, event: dict[str, Any]) -> bool:
        if owned_scan_reason(event):
            return False
        return original_should_emit(self, event)

    @wraps(original_append)
    def append(self, event: dict[str, Any]) -> None:
        if owned_scan_reason(event):
            return
        original_append(self, event)

    ble_event_log.BleEventDeduper.should_emit = should_emit
    ble_event_log.BleEventLog.append = append
    ble_event_log._koalabyte_owned_filter_installed = True


def _install_koala_kapture_filter() -> None:
    from . import koala_kapture

    if getattr(koala_kapture, "_koalabyte_owned_filter_installed", False):
        return
    original = koala_kapture.KoalaKaptureRecorder._matches_filter

    @wraps(original)
    def matches_filter(self, *, name: str, address: str) -> bool:
        if owned_scan_reason(name=name, address=address):
            return False
        return original(self, name=name, address=address)

    koala_kapture.KoalaKaptureRecorder._matches_filter = matches_filter
    koala_kapture._koalabyte_owned_filter_installed = True


def _install_anteater_filter() -> None:
    from . import anteater

    if getattr(anteater, "_koalabyte_owned_filter_installed", False):
        return
    original_assess = anteater.assess_observation
    original_scan = anteater._scan_bleak
    original_load = anteater._load_observations_from_file

    @wraps(original_assess)
    def assess(raw: dict[str, Any], raw_addresses: bool = False):
        observation = original_assess(raw, raw_addresses=raw_addresses)
        reason = owned_scan_reason(raw)
        if reason:
            observation.risk_score = -1
            observation.risk_level = "owned_excluded"
            observation.indicators = [reason]
        return observation

    @wraps(original_scan)
    async def scan(scan_seconds: float, raw_addresses: bool):
        observations, error = await original_scan(scan_seconds, raw_addresses)
        return [item for item in observations if item.risk_level != "owned_excluded"], error

    @wraps(original_load)
    def load(path: Path, raw_addresses: bool, max_records: int = 1000):
        observations = original_load(path, raw_addresses, max_records)
        return [item for item in observations if item.risk_level != "owned_excluded"]

    anteater.assess_observation = assess
    anteater._scan_bleak = scan
    anteater._load_observations_from_file = load
    anteater._koalabyte_owned_filter_installed = True


def _install_kruisin_filter() -> None:
    from . import koala_kombat_kruisin as kruisin

    if getattr(kruisin, "_koalabyte_owned_filter_installed", False):
        return

    original_node_record = kruisin._node_event_to_record
    original_scan_ble = kruisin.scan_ble
    original_scan_wifi_nmcli = kruisin._scan_wifi_nmcli
    original_scan_wifi_iw = kruisin._scan_wifi_iw

    @wraps(original_node_record)
    def node_record(event, fix, *, include_wifi: bool, include_ble: bool):
        if owned_scan_reason(event):
            return None
        return original_node_record(
            event,
            fix,
            include_wifi=include_wifi,
            include_ble=include_ble,
        )

    def filter_records(result):
        records, notes = result
        kept = [
            record
            for record in records
            if not owned_scan_reason(
                name=getattr(record, "name", ""),
                address=getattr(record, "identifier", ""),
                ssid=getattr(record, "name", "")
                if getattr(record, "radio", "") == "wifi"
                else "",
                bssid=getattr(record, "identifier", "")
                if getattr(record, "radio", "") == "wifi"
                else "",
            )
        ]
        excluded = len(records) - len(kept)
        if excluded:
            notes = list(notes) + [
                f"Excluded {excluded} Pi/ESP32/Heltec owned-node observation(s)."
            ]
        return kept, notes

    @wraps(original_scan_ble)
    def scan_ble(fix, duration_seconds=kruisin.DEFAULT_BLE_SECONDS):
        return filter_records(original_scan_ble(fix, duration_seconds))

    @wraps(original_scan_wifi_nmcli)
    def scan_wifi_nmcli(fix):
        return filter_records(original_scan_wifi_nmcli(fix))

    @wraps(original_scan_wifi_iw)
    def scan_wifi_iw(fix):
        return filter_records(original_scan_wifi_iw(fix))

    kruisin._node_event_to_record = node_record
    kruisin.scan_ble = scan_ble
    kruisin._scan_wifi_nmcli = scan_wifi_nmcli
    kruisin._scan_wifi_iw = scan_wifi_iw
    kruisin._koalabyte_owned_filter_installed = True


def _install_bluez_filter() -> None:
    from . import bluez_tools

    if getattr(bluez_tools, "_koalabyte_owned_filter_installed", False):
        return
    original_scan = bluez_tools.scan

    @wraps(original_scan)
    def scan(
        duration_seconds: int = 15,
        output_dir: Path = bluez_tools.DEFAULT_OUTPUT_DIR,
        raw_addresses: bool = False,
    ):
        result = original_scan(
            duration_seconds=duration_seconds,
            output_dir=output_dir,
            raw_addresses=raw_addresses,
        )
        excluded = 0
        for item in result.results:
            item.stdout, stdout_excluded = _filter_bluez_text(item.stdout)
            item.stderr, stderr_excluded = _filter_bluez_text(item.stderr)
            excluded += stdout_excluded + stderr_excluded
        result.safety["owned_koalabyte_nodes_excluded"] = True
        result.safety["owned_scan_exclusion_count"] = excluded
        artifact = Path(result.artifacts.get("scan", ""))
        if artifact:
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(
                json.dumps(asdict(result), indent=2, sort_keys=True),
                encoding="utf-8",
            )
        return result

    bluez_tools.scan = scan
    bluez_tools._koalabyte_owned_filter_installed = True


def install_owned_scan_allowlist() -> tuple[str, ...]:
    global _INSTALLED
    if _INSTALLED:
        return ()

    installers: tuple[tuple[str, Callable[[], None]], ...] = (
        ("ble_event_log", _install_ble_event_filter),
        ("koala_kapture", _install_koala_kapture_filter),
        ("anteater", _install_anteater_filter),
        ("koala_kombat_kruisin", _install_kruisin_filter),
        ("bluez_tools", _install_bluez_filter),
    )
    installed: list[str] = []
    for name, installer in installers:
        installer()
        installed.append(name)
    _INSTALLED = True
    return tuple(installed)
