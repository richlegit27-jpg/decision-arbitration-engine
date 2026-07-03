from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    ROOT / "templates" / "mobile.html",
    ROOT / "static" / "js" / "nova-mobile-app.js",
    ROOT / "static" / "js" / "nova-core.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-events.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-sessions.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-sessions-core.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-final-polish-guard.js",
]

FORBIDDEN = [
    "NOVA_MOBILE_UNIQUE_FINAL_SESSIONS_PANEL_OWNER_20260625",
    "window.switchSession(session.id)",
    "nova-mobile-real-final-sessions-panel-20260625",
]

WATCH = [
    "nova-mobile-sessions-panel",
    "window.NovaOpenMobileSessions",
    "window.NovaCloseMobileSessions",
    "window.switchSession",
    "function openSession",
    "createElement(\"div\")",
    "createElement('div')",
    "panel.id = \"nova-mobile-sessions-panel\"",
    "panel.id = 'nova-mobile-sessions-panel'",
]

def read(path):
    return path.read_text(encoding="utf-8", errors="replace")

def line_hits(path, patterns):
    text = read(path)
    lines = text.splitlines()
    hits = []
    for idx, line in enumerate(lines, start=1):
        for pattern in patterns:
            if pattern in line:
                hits.append((idx, pattern, line.strip()))
    return hits

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

all_text = ""
for path in TARGETS:
    if path.exists():
        all_text += "\n\n--- " + str(path.relative_to(ROOT)) + " ---\n"
        all_text += read(path)

print("NOVA MOBILE SESSIONS FRONTEND OWNER AUDIT")
print("========================================")
print("")

for forbidden in FORBIDDEN:
    check(f"forbidden absent: {forbidden}", forbidden not in all_text)

print("")
print("WATCH HITS")
print("----------")

for path in TARGETS:
    if not path.exists():
        print("MISSING", path.relative_to(ROOT))
        continue

    hits = line_hits(path, WATCH)
    if not hits:
        continue

    print("")
    print(path.relative_to(ROOT))
    for line_no, pattern, line in hits:
        print(f"  L{line_no}: {pattern}: {line[:160]}")

print("")
print("NOVA MOBILE SESSIONS FRONTEND OWNER AUDIT PASSED")
