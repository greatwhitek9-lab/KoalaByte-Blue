Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
path = project / "include" / "config.h"
text = path.read_text(encoding="utf-8")
old = '#define KOALBLUE_FW_VERSION "0.9.7-dualeye-sensitive-killerkoala-menu"'
if old not in text:
    old = '#define KOALABLUE_FW_VERSION "0.9.7-dualeye-sensitive-killerkoala-menu"'
new = '#define KOALABLUE_FW_VERSION "0.9.24-cyber-koala-expression-sync-v2"'
count = text.count(old)
if count != 1:
    raise RuntimeError(
        f"release-version patch expected exactly one firmware version anchor, found {count}"
    )
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print(f"Stamped DualEye firmware version 0.9.24 cyber-koala expression sync v2: {path}")
