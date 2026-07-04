from pathlib import Path
import re

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8")

allowed = [
    "nova-mobile-simple-session-drawer-v1.js",
    "nova-mobile-send-session-authority-v1.js",
    "nova-mobile-url-session-authority-v1.js",
]

script_re = re.compile(r'<script\s+[^>]*src="([^"]+)"[^>]*>\s*</script>', re.IGNORECASE)

disabled = []

def replace_script(match):
    tag = match.group(0)
    src = match.group(1)

    if "/static/js/mobile/" not in src:
        return tag

    src_lower = src.lower()

    if not ("session" in src_lower or "sessions" in src_lower):
        return tag

    if any(name in src for name in allowed):
        return tag

    if "DISABLED LEGACY MOBILE SESSION SCRIPT" in tag:
        return tag

    disabled.append(src)
    return "<!-- DISABLED LEGACY MOBILE SESSION SCRIPT: " + tag + " -->"

new_text = script_re.sub(replace_script, text)

if new_text == text:
    print("No legacy mobile session scripts disabled.")
else:
    path.write_text(new_text, encoding="utf-8")
    print("Disabled legacy mobile session scripts:")
    for src in disabled:
        print(" - " + src)

print("")
print("Kept allowed session scripts:")
for name in allowed:
    print(" - " + name)
