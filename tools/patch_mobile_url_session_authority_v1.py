from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8")

script = '<script src="/static/js/mobile/nova-mobile-url-session-authority-v1.js?v=url-session-authority-20260704"></script>'

if script in text:
    print("URL session authority script already included.")
else:
    marker = "</body>"
    if marker not in text:
        raise SystemExit("Could not find </body> in templates/mobile.html")

    text = text.replace(marker, "    " + script + "\n</body>", 1)
    path.write_text(text, encoding="utf-8")
    print("Included URL session authority script in templates/mobile.html")
