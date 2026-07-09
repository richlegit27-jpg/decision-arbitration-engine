from pathlib import Path
import re

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_REMOVE_COPY_EXPORT_RAW_CSS_20260703"
if marker in text and "#nova-mobile-copy-chat,\n#nova-mobile-export-chat" not in text:
    print("copy/export raw CSS patch already installed")
    raise SystemExit(0)

pattern = re.compile(
    r"\n#nova-mobile-copy-chat,\s*\n#nova-mobile-export-chat\s*\{[^}]*\}",
    re.MULTILINE,
)

text2, count = pattern.subn(
    "\n<!-- " + marker + ": removed malformed raw copy/export CSS block -->",
    text,
)

if count == 0:
    raise SystemExit("copy/export raw CSS block not found")

path.write_text(text2.rstrip() + "\n", encoding="utf-8")
print("removed copy/export raw CSS blocks:", count)
print("patched:", path)
