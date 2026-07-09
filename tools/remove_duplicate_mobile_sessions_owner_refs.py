from pathlib import Path
import re

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")
original = text

remove_names = [
    "nova-core.js",
    "nova-mobile-sessions-core.js",
]

for name in remove_names:
    # Remove full script tags that reference the duplicate owner files.
    pattern = re.compile(
        r'^[ \t]*<script\b[^>]*'
        + re.escape(name)
        + r'[^>]*>\s*</script>[ \t]*\r?\n?',
        re.IGNORECASE | re.MULTILINE,
    )
    text, count = pattern.subn("", text)
    print(f"removed script refs for {name}: {count}")

if text == original:
    print("warning: no duplicate sessions owner script refs removed")

path.write_text(text.rstrip() + "\n", encoding="utf-8")
