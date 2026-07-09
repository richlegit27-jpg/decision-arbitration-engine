from pathlib import Path

TARGET = "nova-chat-width-stability.js"

changed = []

for path in Path("templates").glob("*.html"):
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    if TARGET not in text:
        continue

    lines = text.splitlines()
    kept = [line for line in lines if TARGET not in line]

    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    changed.append(str(path))

js_path = Path("static/js/nova-chat-width-stability.js")
if js_path.exists():
    js_path.unlink()
    changed.append(str(js_path))

print("removed width stability script references:")
for item in changed:
    print("-", item)
