from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8")

script = '<script src="/static/js/mobile/nova-mobile-send-session-authority-v1.js?v=send-session-authority-20260704"></script>'

if script in text:
    print("Send session authority already included.")
else:
    marker = "</body>"
    if marker not in text:
        raise SystemExit("Could not find </body>")

    text = text.replace(marker, "    " + script + "\n</body>", 1)
    path.write_text(text, encoding="utf-8")
    print("Inserted send session authority script.")
