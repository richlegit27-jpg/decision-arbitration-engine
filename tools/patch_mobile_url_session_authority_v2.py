from pathlib import Path
import re

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8")

new_script = '<script src="/static/js/mobile/nova-mobile-url-session-authority-v1.js?v=url-session-authority-v2-20260704"></script>'

pattern = r'<script src="/static/js/mobile/nova-mobile-url-session-authority-v1\.js\?v=[^"]*"></script>'

if re.search(pattern, text):
    text = re.sub(pattern, new_script, text, count=1)
    print("Updated URL session authority script version.")
elif new_script not in text:
    marker = "</body>"
    if marker not in text:
        raise SystemExit("Could not find </body> in templates/mobile.html")
    text = text.replace(marker, "    " + new_script + "\n</body>", 1)
    print("Inserted URL session authority script.")

path.write_text(text, encoding="utf-8")
