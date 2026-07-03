from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_RICHARD_SESSION_STORE_IMPORT_ROUTE_20260703"

if marker not in text:
    print("marker not found; import route already removed")
else:
    marker_index = text.index(marker)

    candidates = [
        text.rfind("\n# ---", 0, marker_index),
        text.rfind("\ntry:", 0, marker_index),
    ]
    candidates = [item for item in candidates if item >= 0]

    if not candidates:
        raise RuntimeError("Could not find start of temporary import route block")

    start = max(candidates)

    # The import route was appended as a temporary EOF repair block.
    text = text[:start].rstrip() + "\n"

    path.write_text(text, encoding="utf-8")
    print("removed temporary import route from app.py")
