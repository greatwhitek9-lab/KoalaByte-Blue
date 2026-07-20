Import("env")

from pathlib import Path
import importlib.util
import re
import unicodedata

project = Path(env.subst("$PROJECT_DIR"))
repo_root = project.parents[1]
catalog_path = repo_root / "pi-companion" / "koalablue" / "menu_catalog.py"
output = project / "include" / "generated_voice_menu_catalog.h"

spec = importlib.util.spec_from_file_location("koalabyte_menu_catalog_build", catalog_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load menu catalog: {catalog_path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def cpp_string(value: object) -> str:
    text = str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
)
TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")


def number_words(value: int) -> str:
    if value < 0:
        return "minus " + number_words(-value)
    if value < 20:
        return ONES[value]
    if value < 100:
        return TENS[value // 10] + (" " + ONES[value % 10] if value % 10 else "")
    if value < 1000:
        return ONES[value // 100] + " hundred" + (" " + number_words(value % 100) if value % 100 else "")
    return " ".join(ONES[int(digit)] for digit in str(value))


def spoken_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " and ").replace("+", " plus ").replace("/", " ")
    text = re.sub(r"\d+", lambda match: " " + number_words(int(match.group(0))) + " ", text)
    text = text.replace("-", " ").replace("_", " ").replace(":", " ")
    text = re.sub(r"[^A-Za-z ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


menu_names = ["main", *list(module.SUBMENU_ITEMS.keys())]
menu_items: list[dict[str, object]] = []
for menu_name in menu_names:
    title = module.submenu_title(menu_name)
    for position, entry in enumerate(module.sorted_menu_entries(menu_name), start=1):
        menu_items.append(
            {
                "menu_name": menu_name,
                "menu_title": title,
                "position": position,
                "label": str(entry.get("label", "Menu item")),
                "command": str(entry.get("command", "")),
                "group": str(entry.get("group", "System / Companion")),
                "enabled": bool(entry.get("enabled", True)),
            }
        )

# KillerKoala is the only sleeping-state phrase. These compact commands are
# accepted only inside the firmware's ten-second wake session. Physical K1-K8
# and trusted Pi keyboard/button menu_sync activity can also open or refresh it.
controls = [
    (100, "k1_main_menu", "Main Menu", "main", "Menu", "K one"),
    (101, "k2_back", "Back", "main", "Back", "K two"),
    (102, "k3_select", "Select", "main", "Select", "K three"),
    (103, "k4_forward", "Forward", "main", "Forward", "K four"),
    (104, "k5_up", "Up", "main", "Up", "K five"),
    (105, "k6_down", "Down", "main", "Down", "K six"),
    (106, "k7_power_toggle", "Power On Off", "main", "Power off", "K seven"),
    (107, "k8_reset", "Reset Reboot", "main", "Reboot", "K eight"),
]

speech_commands: list[tuple[int, str]] = []
routes: list[dict[str, object]] = []
for command_id, command, label, menu_name, natural, key_name in controls:
    speech_commands.extend(((command_id, natural), (command_id, key_name)))
    routes.append(
        {
            "command_id": command_id,
            "command": command,
            "label": label,
            "group": "System / Companion",
            "menu_name": menu_name,
            "phrase": natural,
            "submenu": False,
            "catalog_index": 0xFFFF,
        }
    )

# Preserve both expected natural forms for K1 inside an active wake session.
speech_commands.append((100, "Open menu"))

# One canonical post-wake phrase per distinct visible label. Repeated labels
# would be ambiguous to MultiNet, so they intentionally share the first route.
# Back rows are represented by K2 and do not consume extra phrase slots.
seen_spoken_labels: set[str] = set()
next_command_id = 200
for catalog_index, item in enumerate(menu_items):
    label = str(item["label"])
    command = str(item["command"])
    if not command or label.lower().startswith("back to "):
        continue
    spoken_label = spoken_text(label)
    key = spoken_label.lower()
    if not spoken_label or key in seen_spoken_labels:
        continue
    seen_spoken_labels.add(key)
    is_submenu = command.startswith("submenu:")
    phrase = f"Launch {spoken_label}"
    speech_commands.append((next_command_id, phrase))
    routes.append(
        {
            "command_id": next_command_id,
            "command": command,
            "label": label,
            "group": item["group"],
            "menu_name": item["menu_name"],
            "phrase": phrase,
            "submenu": is_submenu,
            "catalog_index": catalog_index,
        }
    )
    next_command_id += 1

# The wrapper supplies eight base phrases: two wake aliases and six post-wake
# local responses. Keep the complete MultiNet command set below 200 entries.
base_command_count = 8
max_total_commands = 198
if base_command_count + len(speech_commands) > max_total_commands:
    raise RuntimeError(
        "DualEye MultiNet command table exceeds safe capacity: "
        f"base={base_command_count}, generated={len(speech_commands)}, "
        f"total={base_command_count + len(speech_commands)}, max={max_total_commands}. "
        "Deduplicate catalog labels rather than silently dropping menu items."
    )

lines = [
    "#pragma once",
    "// Generated by scripts/generate_voice_menu_catalog.py. Do not edit.",
    "// Voice routes below are post-wake commands gated by a 10-second session.",
    "",
    "struct GeneratedVoiceRoute {",
    "  int commandId;",
    "  const char *command;",
    "  const char *label;",
    "  const char *group;",
    "  const char *menuName;",
    "  const char *phrase;",
    "  bool submenu;",
    "  uint16_t catalogIndex;",
    "};",
    "",
    "struct GeneratedMenuCatalogItem {",
    "  const char *menuName;",
    "  const char *menuTitle;",
    "  const char *group;",
    "  const char *label;",
    "  const char *command;",
    "  uint16_t position;",
    "  bool enabled;",
    "};",
    "",
    "static const sr_cmd_t kGeneratedSpeechCommands[] = {",
]
for command_id, phrase in speech_commands:
    lines.append(f"  {{{command_id}, {cpp_string(phrase)}}},")
lines.extend(
    [
        "};",
        "constexpr size_t kGeneratedSpeechCommandCount =",
        "    sizeof(kGeneratedSpeechCommands) / sizeof(kGeneratedSpeechCommands[0]);",
        "",
        "static const GeneratedVoiceRoute kGeneratedVoiceRoutes[] = {",
    ]
)
for route in routes:
    lines.append(
        "  {"
        f"{route['command_id']}, {cpp_string(route['command'])}, "
        f"{cpp_string(route['label'])}, {cpp_string(route['group'])}, "
        f"{cpp_string(route['menu_name'])}, {cpp_string(route['phrase'])}, "
        f"{'true' if route['submenu'] else 'false'}, {route['catalog_index']}"
        "},"
    )
lines.extend(
    [
        "};",
        "constexpr size_t kGeneratedVoiceRouteCount =",
        "    sizeof(kGeneratedVoiceRoutes) / sizeof(kGeneratedVoiceRoutes[0]);",
        "",
        "static const GeneratedMenuCatalogItem kGeneratedMenuCatalog[] = {",
    ]
)
for item in menu_items:
    lines.append(
        "  {"
        f"{cpp_string(item['menu_name'])}, {cpp_string(item['menu_title'])}, "
        f"{cpp_string(item['group'])}, {cpp_string(item['label'])}, "
        f"{cpp_string(item['command'])}, {item['position']}, "
        f"{'true' if item['enabled'] else 'false'}"
        "},"
    )
lines.extend(
    [
        "};",
        "constexpr size_t kGeneratedMenuCatalogCount =",
        "    sizeof(kGeneratedMenuCatalog) / sizeof(kGeneratedMenuCatalog[0]);",
        "",
        "inline const GeneratedVoiceRoute *generatedVoiceRouteForId(int commandId) {",
        "  for (const auto &route : kGeneratedVoiceRoutes) {",
        "    if (route.commandId == commandId) return &route;",
        "  }",
        "  return nullptr;",
        "}",
        "",
    ]
)

content = "\n".join(lines)
output.parent.mkdir(parents=True, exist_ok=True)
if not output.exists() or output.read_text(encoding="utf-8") != content:
    output.write_text(content, encoding="utf-8")
print(
    "Generated DualEye wake-session voice/menu catalog: "
    f"menus={len(menu_names)}, rows={len(menu_items)}, routes={len(routes)}, "
    f"generated_phrases={len(speech_commands)}, total_multinet={base_command_count + len(speech_commands)}"
)
