from pathlib import Path

tag = '<script src="{{ url_for(\'static\', filename=\'js/mobile/nova-mobile-session-restore-lock.js\') }}?v=session-restore-lock-20260702"></script>'

for rel in ("templates/mobile.html", "templates/index-mobile.html"):
    path = Path(rel)
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    if "nova-mobile-session-restore-lock.js" in text:
        print(f"already wired {rel}")
        continue

    if "</body>" in text:
        text = text.replace("</body>", tag + "\n</body>", 1)
    else:
        text = text.rstrip() + "\n" + tag + "\n"

    path.write_text(text, encoding="utf-8")
    print(f"wired {rel}")
