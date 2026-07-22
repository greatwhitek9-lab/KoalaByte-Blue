Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
path = project / "src" / "integrated_main.cpp"
text = path.read_text(encoding="utf-8")
old = '''  doc["fw"] = KOALABLUE_FW_VERSION;
  doc["touch"] = false;
'''
new = '''  doc["fw"] = KOALABLUE_FW_VERSION;
  doc["protocol"] = KOALABLUE_PROTOCOL;
  doc["repo_protocol_version"] = KOALABLUE_REPO_PROTOCOL_VERSION;
  doc["touch"] = false;
'''
count = text.count(old)
if count != 1:
    raise RuntimeError(
        f"protocol-status patch expected one node-status anchor, found {count}"
    )
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print(f"Patched explicit ESP32 protocol status identifiers: {path}")
