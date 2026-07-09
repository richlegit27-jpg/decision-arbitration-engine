from pathlib import Path
import re

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8")

script = '<script src="/static/js/mobile/nova-mobile-simple-session-drawer-v1.js?v=clean-session-drawer-v3-actions-20260704"></script>'
pattern = r'<script src="/static/js/mobile/nova-mobile-simple-session-drawer-v1\.js\?v=[^"]+"></script>'

if re.search(pattern, text):
    text = re.sub(pattern, script, text, count=1)
elif "</body>" in text:
    text = text.replace("</body>", "    " + script + "\n</body>", 1)
else:
    raise SystemExit("Could not find drawer script or </body>.")

path.write_text(text, encoding="utf-8")
print("Installed clean session drawer v3 actions script.")
