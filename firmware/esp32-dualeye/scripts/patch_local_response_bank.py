Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
path = project / "src" / "integrated_main_wake_session.cpp"
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"local response-bank patch expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """    case LocalVoiceCategory::Wake: return "wake";
    case LocalVoiceCategory::Status: return "status";
    case LocalVoiceCategory::Help: return "help";
    case LocalVoiceCategory::Greeting: return "greeting";
    case LocalVoiceCategory::Thanks: return "thanks";
    case LocalVoiceCategory::Banter: return "banter";
    case LocalVoiceCategory::Escalate: return "escalate";
""",
    """    case LocalVoiceCategory::Wake: return "wake";
    case LocalVoiceCategory::Status: return "status";
    case LocalVoiceCategory::Help: return "help";
    case LocalVoiceCategory::Acknowledgement: return "acknowledgement";
    case LocalVoiceCategory::Banter: return "banter";
    case LocalVoiceCategory::Success: return "success";
    case LocalVoiceCategory::Error: return "error";
    case LocalVoiceCategory::Escalate: return "escalate";
""",
    "category-name switch",
)

greeting_count = text.count("LocalVoiceCategory::Greeting")
thanks_count = text.count("LocalVoiceCategory::Thanks")
if greeting_count < 1 or thanks_count < 1:
    raise RuntimeError(
        f"expected acknowledgement aliases, found greeting={greeting_count}, thanks={thanks_count}"
    )
text = text.replace("LocalVoiceCategory::Greeting", "LocalVoiceCategory::Acknowledgement")
text = text.replace("LocalVoiceCategory::Thanks", "LocalVoiceCategory::Acknowledgement")

replace_once(
    """  doc["generated_menu_rows"] = kGeneratedMenuCatalogCount;
  doc["basic_response_owner"] = "esp32-s3";
""",
    """  doc["generated_menu_rows"] = kGeneratedMenuCatalogCount;
  doc["local_response_count"] = localVoiceResponseTotalCount();
  doc["local_response_history_depth"] = localVoiceRecentHistoryDepth();
  doc["local_response_repeat_policy"] =
      "exclude_previous_three_responses_per_category";
  doc["basic_response_owner"] = "esp32-s3";
""",
    "response-bank status diagnostics",
)

replace_once(
    'doc["audio_source"] = "embedded_en_au_william_neural_mulaw";',
    'doc["audio_source"] = "embedded_en_au_william_neural_mulaw_40_clip_bank";',
    "audio source identifier",
)

if "LocalVoiceCategory::Greeting" in text or "LocalVoiceCategory::Thanks" in text:
    raise RuntimeError("legacy response aliases remain")

path.write_text(text, encoding="utf-8")
print(
    f"Patched 40-clip local response bank: {path}; aliases={greeting_count + thanks_count}"
)
