from pathlib import Path


TARGET = Path("app.py")
MARKER = "# NOVA_PROJECT_BRAIN_DECISION_LOG_ROUTE_KEYWORDS_20260701"

if not TARGET.exists():
    raise SystemExit("missing app.py")

lines = TARGET.read_text(encoding="utf-8-sig").splitlines()

start = None
end = None

for index, line in enumerate(lines):
    if MARKER in line:
        start = index
        break

if start is None:
    print("stale Decision Log route keyword helper already removed")
    raise SystemExit(0)

for index in range(start, len(lines)):
    if "return any(keyword in text for keyword in NOVA_PROJECT_BRAIN_DECISION_LOG_ROUTE_KEYWORDS_20260701)" in lines[index]:
        end = index + 1
        break

if end is None:
    raise SystemExit("found marker but could not find helper return line")

new_lines = lines[:start] + lines[end:]

TARGET.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")

print(f"removed stale Decision Log route keyword helper from app.py lines {start + 1}-{end}")
