#!/usr/bin/env python3
"""Hardware-free source contract for the Settings > AI online-mode switch."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi-companion"))

from koalablue import menu_actionability, menu_catalog


def main() -> int:
    paths = [
        ROOT / "scripts" / "koalabyte_ai_mode_admin.py",
        ROOT / "pi-companion" / "koalablue" / "menu_action_runner.py",
        ROOT / "pi-companion" / "koalablue" / "menu_actionability.py",
    ]
    for path in paths:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    main_commands = menu_catalog.menu_commands("main")
    assert "submenu:settings" in main_commands
    assert "submenu:ai" in menu_catalog.menu_commands("settings")
    ai_entries = menu_catalog.sorted_menu_entries("ai")
    labels = {str(row["label"]): str(row["command"]) for row in ai_entries}
    assert labels.get("Online AI ON") == "ai_online_on"
    assert labels.get("Online AI OFF") == "ai_online_off"
    assert labels.get("AI Mode Status") == "ai_mode_status"
    for command in ("ai_online_on", "ai_online_off", "ai_mode_status"):
        capability = menu_actionability.classify_command(command)
        assert capability["concrete"], (command, capability)

    helper = (ROOT / "scripts" / "koalabyte_ai_mode_admin.py").read_text(encoding="utf-8")
    runner = (ROOT / "pi-companion" / "koalablue" / "menu_action_runner.py").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "install_esp32_dualeye_voice_bridge_service.sh").read_text(encoding="utf-8")
    assert 'sys.argv[1] not in {"local", "online", "status"}' in helper
    assert "AI_MODE_NEEDS_API_KEY" in helper
    assert '["systemctl", "restart", SERVICE]' in helper
    assert '["sudo", "-n", helper, operation]' in runner
    assert "/etc/sudoers.d/koalabyte-ai-mode" in installer
    assert "visudo -cf" in installer
    print("AI_MENU_TOGGLE_SOURCE_CONTRACT_PASS")
    print("Settings > AI submenu, API-key guard, restart, and restricted sudo rule PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
