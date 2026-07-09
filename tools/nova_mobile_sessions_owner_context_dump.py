from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RANGES = [
    ("static/js/nova-mobile-app.js", 430, 490),
    ("static/js/nova-mobile-app.js", 8040, 8110),
    ("static/js/nova-mobile-app.js", 8445, 8505),
    ("static/js/nova-core.js", 1, 110),
    ("static/js/mobile/nova-mobile-sessions-core.js", 1, 170),
    ("static/js/mobile/nova-mobile-sessions.js", 180, 430),
    ("static/js/mobile/nova-mobile-sessions.js", 1680, 1770),
]

def show(rel, start, end):
    path = ROOT / rel
    if not path.exists():
        print("")
        print("MISSING", rel)
        return

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    print("")
    print("=" * 100)
    print(f"{rel}:{start}-{end}")
    print("=" * 100)

    for idx in range(max(1, start), min(len(lines), end) + 1):
        print(f"{idx:05d}: {lines[idx - 1]}")

for rel, start, end in RANGES:
    show(rel, start, end)
