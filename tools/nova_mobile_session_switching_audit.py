from pathlib import Path

print("NOVA MOBILE SESSION SWITCHING AUDIT")
print("===================================")

targets = [
    Path("static/js/mobile/nova-mobile-sessions.js"),
    Path("static/js/mobile/nova-mobile-state.js"),
    Path("static/js/mobile/nova-mobile-chat-ui.js"),
    Path("static/js/nova-mobile-app.js"),
    Path("templates/mobile.html"),
]

needles = [
    "api/sessions",
    "switch",
    "active_session",
    "activeSession",
    "session_id",
    "localStorage",
    "render",
    "messages",
    "New Chat",
]

for path in targets:
    print("")
    print("FILE", path)

    if not path.exists():
        print("MISSING")
        continue

    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    print("lines", len(lines))

    for needle in needles:
        hits = []

        for index, line in enumerate(lines, start=1):
            if needle.lower() in line.lower():
                hits.append(index)

        if hits:
            shown = hits[:12]
            extra = "" if len(hits) <= 12 else f" +{len(hits) - 12} more"
            print(f"  {needle}: {shown}{extra}")

print("")
print("NOVA MOBILE SESSION SWITCHING AUDIT COMPLETE")
