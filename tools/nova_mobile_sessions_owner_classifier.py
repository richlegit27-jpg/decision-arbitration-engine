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

DANGER_PATTERNS = [
    "innerHTML",
    "appendChild",
    "replaceChildren",
    "insertAdjacentHTML",
    "panel.id =",
    "document.body.appendChild(panel)",
    "window.switchSession",
    "window.NovaOpenMobileSessions",
    "window.NovaCloseMobileSessions",
    "function openSession",
    "function openSessions",
    "async function openSession",
    "async function openSessions",
    "openSessionsPanel",
    "openSessionsFinal",
    "loadSessionsPanel",
]

SAFE_PATTERNS = [
    "getElementById(\"nova-mobile-sessions-panel\")",
    "getElementById('nova-mobile-sessions-panel')",
    "closest(\"#nova-mobile-sessions-panel\")",
    "closest('#nova-mobile-sessions-panel')",
    "forceHide($(\"nova-mobile-sessions-panel\"))",
]

def read(path):
    return path.read_text(encoding="utf-8", errors="replace")

def hits(path, patterns):
    out = []
    lines = read(path).splitlines()
    for idx, line in enumerate(lines, start=1):
        for pattern in patterns:
            if pattern in line:
                out.append((idx, pattern, line.strip()))
    return out

print("NOVA MOBILE SESSIONS OWNER CLASSIFIER")
print("====================================")
print("")

for path in TARGETS:
    if not path.exists():
        continue

    danger = hits(path, DANGER_PATTERNS)
    safe = hits(path, SAFE_PATTERNS)

    if not danger and not safe:
        continue

    print(path.relative_to(ROOT))
    print("-" * len(str(path.relative_to(ROOT))))

    if danger:
        print("DANGER / OWNER-LIKE HITS:")
        for line_no, pattern, line in danger:
            print(f"  L{line_no}: {pattern}: {line[:180]}")

    if safe:
        print("SAFE / READER-LIKE HITS:")
        for line_no, pattern, line in safe:
            print(f"  L{line_no}: {pattern}: {line[:180]}")

    print("")

print("NOVA MOBILE SESSIONS OWNER CLASSIFIER COMPLETE")
