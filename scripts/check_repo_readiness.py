#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

EXPECTED_MENU_LABELS = [
    "Scan",
    "Summary",
    "Show Devices",
    "eucalyptus Status",
    "eucalyptus Start",
    "eucalyptus Stop",
    "eucalyptus Restart",
    "eucalyptus Upload Status",
    "Eucalyptus Mode",
    "Koala Kapture",
    "Koala Kry",
    "Koala Kry RF Review",
    "Ear Tag",
    "KoalaByte Lab",
    "Koala Mode Switcher",
    "Koala Kan Kommander",
    "Gumleaf Gear Check",
    "Eucalyptus Bus Scout",
    "Dropbear Discovery Sweep",
    "Billabong HCI Watch",
    "Kookaburra Safe Nest Run",
    "that’s not a knife",
    "KillerKoala Voice",
    "Urban Poaching",
    "Buttons",
    "Level / Status",
    "Report",
    "Boomerang",
    "Wake killerkoala",
    "Authorized BLE Inventory",
    "GATT Readiness Checklist",
    "Pairing Security Review",
    "Lab Beacon Plan",
    "Packet Capture Notes",
    "Defensive Lab Report",
    "Restricted Placeholder",
    "Settings",
    "Lab",
    "Shutdown",
    "Quit",
]

SELOKY_PD_ITEM = "Seloky USB-C PD Trigger Board Module PD/QC Decoy Fast Charge USB Type-C to 12V"
INNOMAKER_ITEM = "InnoMaker USB to CAN Converter kit"

EXPECTED_BOM_ITEMS = [
    "Raspberry Pi 3 Model B+",
    "Nordic nRF52840 USB Dongle / PCA10059 / NRF52840-DONGLE",
    "ESP32-S3 DualEye module",
    "1.28 inch round LCD display",
    "8 ohm 2 W mini speaker",
    "2.4 GHz external antenna",
    "Adafruit tactile button switch 6mm pack PID 367",
    "KoalaByte Blue front button bezel 6x6mm RevA6",
    "Protected 18650 Li-ion cell",
    "2x18650 holder with protection / BMS",
    SELOKY_PD_ITEM,
    "5 V 3 A buck converter",
    "Inline rated power switch",
    "microSD card",
    "USB and JST power/data cables",
    "M2.5 standoffs / screws / nuts",
    "Acrylic or printed frame plates",
    "3D printed case / stacked frame / rear panel",
    INNOMAKER_ITEM,
    "InnoMaker CAN cable / adapter-side harness",
    "Adapter mount / strain relief",
    "Cable management / strain relief",
]

REQUIRED_TEXT = {
    "README.md": ["RevA25", "InnoMaker USB to CAN Converter kit", "bench-simulator", "flash_all_components.sh"],
    "docs/KOALA_KAN_KOMMANDER_REVA22.md": ["RevA25", "InnoMaker USB to CAN Converter kit", "listen-transmit", "--confirm-transmit"],
    "docs/FLASHING.md": ["flash_all_components.sh", "InnoMaker USB to CAN Converter kit", "KoalaByte Lab"],
    "docs/THEME_AND_MENU_SYSTEM.md": ["jungle_jumanji_eucalyptus", "No overlapping words", "KOALABYTE BLUE title at the top"],
    "docs/KOALA_BLUEZ_TOOLS_REVA16.md": ["RevA18 Outback BlueZ Module Deck", "Gumleaf Gear Check", "Eucalyptus Bus Scout", "--owned-device"],
    "docs/NRF52840_DONGLE_FLASHING.md": ["nrf52840dongle_nrf52840", "flash_nrf52840_dongle_lab_dfu.sh", "KoalaByte Lab"],
    "docs/EAR_TAG_TX_LAB_REVA15.md": ["KoalaByte Lab", "KBTX", "does not replay captured packets"],
    "docs/KOALA_KONNECT_REVA20.md": ["Koala Konnect", "hci_usb", "koala-konnect-nrf52840-dongle-dfu.zip"],
    "docs/ORDERABLE_PARTS_LIST.md": ["Seloky USB-C PD Trigger Board", "InnoMaker USB-to-CAN kit", "Do not connect 12V directly to the Pi"],
    "docs/POWER_UPDATE_REVA2.md": ["Seloky USB-C PD/QC 12V trigger board", "Replaces the prior USB-C PD breakout reference", "Verify 12V output"],
    "docs/PRODUCTION_FILES.md": ["production/RevA17-dongle-only/", "No custom PCB"],
    "docs/CAMERA_AWARENESS_LOGGER.md": ["Boomerang", "manual/public-observation only", "does not collect"],
    "docs/EUCALYPTUS_ALWAYS_ON_BLE_REVA8.md": ["Eucalyptus Mode", "Koalagotchi", "always-on Bluetooth scanner and logger"],
    "production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv": ["Seloky USB-C PD Trigger Board Module", "InnoMaker USB to CAN Converter kit", "Koala Kan Kommander"],
    "production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md": ["InnoMaker USB to CAN Converter kit", "5 V buck converter"],
    "production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv": ["Seloky trigger output", "KoalaByte Lab", "Koala Mode Switcher"],
    "firmware/esp32-dualeye/platformio.ini": ["bodmer/TFT_eSPI"],
    "firmware/esp32-dualeye/src/main.cpp": ["runBootAnimation();", "ENABLE_DISPLAY_BOOT_ANIMATION"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/CMakeLists.txt": ["find_package(Zephyr REQUIRED", "target_sources(app PRIVATE src/main.c)"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/prj.conf": ["KoalaByte Lab", "CONFIG_BT_PERIPHERAL=y"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c": ["KBTX", "bt_le_adv_start", "no captured packet replay"],
    "pi-companion/koalablue/bluez_tools.py": ["BLUEZ_MODULES", "Gumleaf Gear Check", "Eucalyptus Bus Scout", "Billabong HCI Watch", "owned_device_required"],
    "pi-companion/koalablue/ble_defense_guard.py": ["ACTION_NAME", "that’s not a knife", "XP_REWARD", "defensive_block_successful"],
    "pi-companion/koalablue/menu_catalog.py": ["Koala Mode Switcher", "KoalaByte Lab", "bench-simulator transmit", "that’s not a knife", "Boomerang", "Eucalyptus Mode"],
    "pi-companion/koalablue/eucalyptus_cyberpet.py": ["ACTION_NAME = \"Eucalyptus Mode\"", "Koalagotchi", "full-color", "run_graphical"],
    "pi-companion/koalablue/boomerang.py": ["ACTION_NAME = \"Boomerang\"", "stays open", "run_interactive"],
    "pi-companion/koalablue/camera_awareness_logger.py": ["manual/public-observation only", "CameraObservation", "MAC_PATTERN"],
    "pi-companion/koalablue/koala_mode_switcher.py": ["Koala Mode Switcher", "KoalaByte Lab", "Koala Konnect", "dongle_mode_state.json"],
    "pi-companion/koalablue/koala_kan_kommander.py": ["ADAPTER_NAME", "InnoMaker USB to CAN Converter kit", "listen_transmit", "confirm_transmit"],
    "pi-companion/config.default.json": ["Outback BlueZ Module Deck", "KoalaByte Lab", "Koala Mode Switcher", "transmit_enabled", "killerkoala_companion", "Boomerang", "Eucalyptus Mode"],
    "scripts/run_boomerang.py": ["koalablue.boomerang", "run_cli"],
    "scripts/run_eucalyptus_cyberpet.py": ["eucalyptus_cyberpet", "run_cli"],
    "scripts/run_camera_awareness_logger.py": ["camera_awareness_logger", "run_cli"],
    "scripts/check_camera_awareness_logger.py": ["MAC-like values must be rejected", "Camera awareness logger smoke check passed"],
    "scripts/check_eucalyptus_cyberpet.py": ["Eucalyptus cyberpet smoke check passed"],
    "scripts/run_thats_not_a_knife.py": ["ble_defense_guard", "run_cli"],
    "scripts/run_thats_not_a_knife_loop.py": ["run_guard_once", "xp_cooldown", "defensive_block_successful"],
    "scripts/install_thats_not_a_knife_service.sh": ["koalabyte-thats-not-a-knife.service", "systemctl", "set -euo pipefail"],
    "systemd/koalabyte-thats-not-a-knife.service.in": ["run_thats_not_a_knife_loop.py", "Restart=always"],
    "scripts/flash_all_components.sh": ["--all", "--nrf-lab", "NO_MONITOR", "Koala Kan Kommander InnoMaker CAN manifest check"],
    "scripts/build_firmware_all.sh": ["check_repo_readiness.py", "pio run", "build_nrf52840_dongle_lab.sh"],
    "scripts/build_nrf52840_dongle_lab.sh": ["REPO_ROOT", "west build", "nrf52840dongle_nrf52840"],
    "scripts/flash_nrf52840_dongle_lab_dfu.sh": ["REPO_ROOT", "nrfutil", "koalabyte-blue-nrf52840-dongle-dfu.zip", "NRF_DFU_PORT"],
    "scripts/flash_esp32.sh": ["NO_MONITOR", "ESP32_PORT", "pio run"],
    "scripts/install_pi.sh": ["check_repo_readiness.py", "can-utils", "run_koala_kan_kommander.py manifest", "install_thats_not_a_knife_service.sh"],
}

OPTIONAL_REQUIRED_TEXT = {
    "pi-companion/koalablue/killerkoala_vocabulary.py": ["KoalaByte Lab", "koalabyte_lab", "lab"],
}

OBSOLETE_PATHS = [
    "docs/NRF52840_DK_FLASHING.md",
    "docs/NRF52840_DK_OPTION_REVA4.md",
    "docs/BOOT_ANIMATION_REVA13.md",
    "docs/MENU_THEME_REVA14.md",
    "docs/MENU_SELECTION_REVA12.md",
    "firmware/nrf52840-dk-lab-peripheral/CMakeLists.txt",
    "firmware/nrf52840-dk-lab-peripheral/prj.conf",
    "firmware/nrf52840-dk-lab-peripheral/src/main.c",
    "firmware/nrf52840-dk-lab-peripheral/README.md",
    "scripts/build_nrf52840_dk_lab.sh",
    "scripts/flash_nrf52840_dk_lab.sh",
    "production/RevA1-nrf52840-dongle/BOM_RevA1.csv",
    "production/RevA1-nrf52840-dongle/ORDERABLE_PARTS_LIST_RevA3.csv",
    "production/RevA11-no-nrf-no-generic-lcd/BOM_RevA11_NoNRF_NoGenericLCD.csv",
]

FORBIDDEN_TEXT = [
    "nrf52840dk_nrf52840",
    "PCA10056",
    "nRF52840 DK",
    "build_nrf52840_dk_lab.sh",
    "flash_nrf52840_dk_lab.sh",
    "firmware/nrf52840-dk-lab-peripheral",
    "production/RevA1-nrf52840-dongle",
    "production/RevA11-no-nrf-no-generic-lcd",
    "HUSB238",
    "USB Type C Power Delivery Dummy Breakout",
    "Adafruit Product ID 5807",
    "EarTag-TX-Lab",
    "Ear Tag TX Lab",
    "USB-C PD charging module",
]


def check_required_text(failures: list[str]) -> None:
    merged = dict(REQUIRED_TEXT)
    for path, needles in OPTIONAL_REQUIRED_TEXT.items():
        if (REPO_ROOT / path).exists():
            merged[path] = needles
    for relative_path, needles in merged.items():
        path = REPO_ROOT / relative_path
        if not path.exists():
            failures.append(f"missing required file: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                failures.append(f"missing '{needle}' in {relative_path}")


def check_obsolete_paths(failures: list[str]) -> None:
    for relative_path in OBSOLETE_PATHS:
        if (REPO_ROOT / relative_path).exists():
            failures.append(f"obsolete file still present: {relative_path}")


def check_forbidden_text(failures: list[str]) -> None:
    ignored_dirs = {".git", ".pio", "build", "__pycache__", ".venv"}
    ignored_files = {"check_repo_readiness.py"}
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or any(part in ignored_dirs for part in path.parts) or path.name in ignored_files:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        for line_no, line in enumerate(lines, start=1):
            for needle in FORBIDDEN_TEXT:
                if needle in line:
                    failures.append(f"forbidden legacy reference '{needle}' found in {rel}:{line_no}: {line.strip()[:160]}")


def check_json_config(failures: list[str]) -> None:
    path = REPO_ROOT / "pi-companion" / "config.default.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"config.default.json is invalid JSON: {exc}")
        return

    configured_items = config.get("menu_selection", {}).get("items", [])
    unknown = [item for item in configured_items if item not in EXPECTED_MENU_LABELS]
    if unknown:
        failures.append(f"menu_selection.items contains unknown labels: {unknown}")

    if config.get("koala_kry", {}).get("rf_transmission") is not False:
        failures.append("Koala Kry must remain offline with rf_transmission=false")
    companion = config.get("killerkoala_companion", {})
    if companion.get("display_name") != "killerkoala":
        failures.append("killerkoala companion display_name is not killerkoala")
    if companion.get("voice_profile", {}).get("accent") != "Australian male":
        failures.append("killerkoala voice profile accent is not Australian male")

    eucalyptus_mode = config.get("eucalyptus_mode", {})
    if eucalyptus_mode.get("display_name") != "Eucalyptus Mode":
        failures.append("eucalyptus_mode display_name must be Eucalyptus Mode")
    if eucalyptus_mode.get("full_color_graphics") is not True:
        failures.append("Eucalyptus Mode must enable full_color_graphics")
    if eucalyptus_mode.get("idle_behavior", {}).get("idle_seconds_before_grumble") != 180:
        failures.append("Eucalyptus Mode idle grumble threshold must be 180 seconds")
    if eucalyptus_mode.get("eating_behavior", {}).get("contentment_increases_per_new_observation") is not True:
        failures.append("Eucalyptus Mode must increase contentment when new observations appear")

    lab_mode = config.get("ear_tag_tx_lab", {})
    if lab_mode.get("firmware_path") != "firmware/nrf52840-dongle-ear-tag-tx-lab":
        failures.append("KoalaByte Lab firmware_path must point to the dongle-only firmware path")
    if lab_mode.get("display_name") != "KoalaByte Lab" or lab_mode.get("device_name") != "KoalaByte Lab":
        failures.append("KoalaByte Lab display_name/device_name must be KoalaByte Lab")

    switcher = config.get("koala_mode_switcher", {})
    if switcher.get("default_mode") != "koalabyte_lab":
        failures.append("Koala Mode Switcher default_mode must be koalabyte_lab")

    kan = config.get("koala_kan_kommander", {})
    if kan.get("display_name") != "Koala Kan Kommander":
        failures.append("koala_kan_kommander display_name must be Koala Kan Kommander")
    if kan.get("default_interface") != "can0":
        failures.append("Koala Kan Kommander default_interface must be can0")
    if kan.get("physical_adapter") != INNOMAKER_ITEM:
        failures.append("Koala Kan Kommander physical_adapter must be the InnoMaker USB to CAN Converter kit")
    if kan.get("observe_only") is not False:
        failures.append("Koala Kan Kommander observe_only must be false for gated bench simulator transmit")
    if kan.get("transmit_enabled") is not True:
        failures.append("Koala Kan Kommander transmit_enabled must be true")
    if kan.get("transmit_requires_bench_simulator") is not True or kan.get("transmit_requires_explicit_confirmation") is not True:
        failures.append("Koala Kan Kommander transmit gates must remain enabled")

    boomerang = config.get("boomerang", {})
    if boomerang.get("display_name") != "Boomerang":
        failures.append("boomerang display_name must be Boomerang")
    if boomerang.get("interactive_stays_open_until_quit") is not True:
        failures.append("boomerang must stay open until the operator quits")
    if boomerang.get("matching_behavior_settings", {}).get("verbal_alerts_enabled_by_default") is not True:
        failures.append("boomerang matching behavior settings must enable verbal alerts by default")
    if boomerang.get("xp_reward_per_logged_record") != 10:
        failures.append("boomerang xp_reward_per_logged_record must be 10")


def check_menu_catalog(failures: list[str]) -> None:
    try:
        from koalablue.menu_catalog import FUNCTION_MENU_ITEMS, menu_labels
    except Exception as exc:
        failures.append(f"failed to import menu catalog: {exc}")
        return
    if menu_labels() != EXPECTED_MENU_LABELS:
        failures.append("menu_catalog.menu_labels() does not match expected menu ordering")
    descriptions = "\n".join(str(item.get("description", "")) for item in FUNCTION_MENU_ITEMS)
    for needle in ("bench-simulator transmit", "that’s not a knife", "stays open until quit", "Koalagotchi always-on Bluetooth scanner and logger"):
        if needle not in descriptions and needle not in "\n".join(menu_labels()):
            failures.append(f"menu catalog missing expected text: {needle}")


def check_bluez_module_registry(failures: list[str]) -> None:
    try:
        from koalablue.bluez_tools import BLUEZ_MODULES, BLUEZ_TOOLS, redact_addresses
    except Exception as exc:
        failures.append(f"failed to import Outback BlueZ Module Deck: {exc}")
        return
    titles = {module.theme_title for module in BLUEZ_MODULES}
    for title in {"Gumleaf Gear Check", "Eucalyptus Bus Scout", "Dropbear Discovery Sweep", "Billabong HCI Watch", "Kookaburra Safe Nest Run"}:
        if title not in titles:
            failures.append(f"Outback BlueZ module registry missing title: {title}")
    helper_names = {tool.koala_name for tool in BLUEZ_TOOLS}
    if "Eucalyptus D-Bus Scout" not in helper_names:
        failures.append("BlueZ helper registry missing Eucalyptus D-Bus Scout")
    if "AA:BB:CC:DD:EE:FF" in redact_addresses("AA:BB:CC:DD:EE:FF"):
        failures.append("BlueZ address redaction did not hash a sample address")


def check_ble_guard(failures: list[str]) -> None:
    try:
        from koalablue.ble_defense_guard import ACTION_NAME, KILLERKOALA_ALERT, XP_REWARD, run_guard_once
    except Exception as exc:
        failures.append(f"failed to import that’s not a knife guard: {exc}")
        return
    if ACTION_NAME != "that’s not a knife":
        failures.append("that’s not a knife action name mismatch")
    if KILLERKOALA_ALERT != "Crikey’ mate. i blocked a SKID!":
        failures.append("killerkoala guard alert mismatch")
    if XP_REWARD <= 0:
        failures.append("that’s not a knife XP reward must be positive")
    inactive = run_guard_once(metrics={}, output_dir="logs/readiness_thats_not_a_knife", state_path="logs/readiness_thats_not_a_knife/guard_state.json", block_path="logs/readiness_thats_not_a_knife/block_state.json", xp_path="logs/readiness_thats_not_a_knife/xp_state.json", award_xp=True)
    if inactive.xp_reward != 0 or inactive.xp_after != inactive.xp_before:
        failures.append("that’s not a knife must not award XP while only monitoring")
    active = run_guard_once(metrics={"connection_errors": 5, "repeated_connects": 8}, output_dir="logs/readiness_thats_not_a_knife", state_path="logs/readiness_thats_not_a_knife/guard_state.json", block_path="logs/readiness_thats_not_a_knife/block_state.json", xp_path="logs/readiness_thats_not_a_knife/xp_state.json", award_xp=False)
    if active.status != "BLOCKED" or not active.defensive_block_successful:
        failures.append("that’s not a knife guard did not complete a defensive block for readiness metrics")
    if active.xp_reward != 0 or active.xp_after != active.xp_before:
        failures.append("that’s not a knife must not award XP when XP awards are disabled")


def check_kan_module(failures: list[str]) -> None:
    try:
        from koalablue.koala_kan_kommander import ADAPTER_NAME, DISPLAY_NAME, manifest, transmit
    except Exception as exc:
        failures.append(f"failed to import Koala Kan Kommander: {exc}")
        return
    if DISPLAY_NAME != "Koala Kan Kommander":
        failures.append("Koala Kan Kommander display name mismatch")
    if ADAPTER_NAME != INNOMAKER_ITEM:
        failures.append("Koala Kan Kommander adapter name mismatch")
    data = manifest("logs/readiness_koala_kan_kommander")
    if data.get("physical_connection", {}).get("recommended_adapter") != INNOMAKER_ITEM:
        failures.append("Koala Kan Kommander manifest adapter mismatch")
    safe_defaults = data.get("safe_defaults", {})
    if safe_defaults.get("transmit_enabled") is not True:
        failures.append("Koala Kan Kommander manifest must enable gated transmit")
    if safe_defaults.get("transmit_requires_bench_simulator") is not True or safe_defaults.get("transmit_requires_explicit_confirmation") is not True:
        failures.append("Koala Kan Kommander manifest transmit gates must remain true")
    blocked = transmit(output_dir="logs/readiness_koala_kan_kommander")
    if blocked.get("status") != "blocked":
        failures.append("Koala Kan Kommander transmit must block without explicit gates")


def check_eucalyptus_mode_module(failures: list[str]) -> None:
    try:
        from koalablue.eucalyptus_cyberpet import ACTION_NAME, DESCRIPTION, EucalyptusStats, CyberPetState, render_tamagotchi_screen, update_pet_state
    except Exception as exc:
        failures.append(f"failed to import Eucalyptus Mode cyberpet: {exc}")
        return
    if ACTION_NAME != "Eucalyptus Mode":
        failures.append("Eucalyptus Mode action name mismatch")
    if "Koalagotchi" not in DESCRIPTION:
        failures.append("Eucalyptus Mode description must mention Koalagotchi")
    stats = EucalyptusStats(observation_count=5, newest_mtime=0.0, files_seen=1, source_dirs=[])
    state = CyberPetState(contentment=50, total_observations_seen=3, last_observation_count=3, last_new_data_time=0.0, direction=1, position=0, mood="scouting", boomerang_throws=0, updated_at=0.0)
    updated, delta, _grumble, mood = update_pet_state(state, stats, idle_seconds=180, branch_width=60)
    if delta != 2 or updated.contentment <= state.contentment or "eating" not in mood:
        failures.append("Eucalyptus Mode must increase contentment when passive observations increase")
    frame = render_tamagotchi_screen(updated, stats, delta=delta, width=72)
    if "EUCALYPTUS MODE" not in frame or "KOALAGOTCHI" not in frame:
        failures.append("Eucalyptus Mode terminal frame missing expected title")


def check_boomerang_module(failures: list[str]) -> None:
    try:
        from koalablue.boomerang import ACTION_NAME, DESCRIPTION, SCOPE
        from koalablue.camera_awareness_logger import create_observation
    except Exception as exc:
        failures.append(f"failed to import Boomerang camera awareness logger: {exc}")
        return
    if ACTION_NAME != "Boomerang":
        failures.append("Boomerang action name mismatch")
    if "stays open" not in DESCRIPTION:
        failures.append("Boomerang description must mention that it stays open")
    if "no RF scanning" not in SCOPE:
        failures.append("Boomerang scope must block RF scanning")
    try:
        create_observation(label="bad", notes="MAC address 00:11:22:33:44:55")
    except ValueError:
        pass
    else:
        failures.append("Boomerang logger must reject MAC-like identifiers")


def check_current_bom(failures: list[str]) -> None:
    path = REPO_ROOT / "production" / "RevA17-dongle-only" / "BOM_RevA17_DongleOnly.csv"
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    except Exception as exc:
        failures.append(f"failed to read current BOM: {exc}")
        return
    actual_items = {row.get("Item", "").strip() for row in rows}
    for item in EXPECTED_BOM_ITEMS:
        if item not in actual_items:
            failures.append(f"current BOM missing item: {item}")


def check_flash_helpers(failures: list[str]) -> None:
    helpers = [
        "scripts/flash_all_components.sh",
        "scripts/flash_esp32.sh",
        "scripts/build_nrf52840_dongle_lab.sh",
        "scripts/flash_nrf52840_dongle_lab_dfu.sh",
        "scripts/build_firmware_all.sh",
        "scripts/install_pi.sh",
        "scripts/install_thats_not_a_knife_service.sh",
    ]
    for helper in helpers:
        path = REPO_ROOT / helper
        if not path.exists():
            failures.append(f"missing flash helper: {helper}")
            continue
        text = path.read_text(encoding="utf-8")
        if "set -euo pipefail" not in text:
            failures.append(f"flash helper missing strict shell mode: {helper}")


def main() -> int:
    failures: list[str] = []
    check_required_text(failures)
    check_obsolete_paths(failures)
    check_forbidden_text(failures)
    check_json_config(failures)
    check_menu_catalog(failures)
    check_bluez_module_registry(failures)
    check_ble_guard(failures)
    check_kan_module(failures)
    check_eucalyptus_mode_module(failures)
    check_boomerang_module(failures)
    check_current_bom(failures)
    check_flash_helpers(failures)

    if failures:
        print("KoalaByte Blue repo readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("KoalaByte Blue repo readiness check passed.")
    print("Ready-to-flash file wiring is present for ESP32, nRF52840 Dongle/DFU, Pi companion, approved theme assets, Eucalyptus Mode, Boomerang, Koala Kan Kommander, and the that’s not a knife local guard service.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
