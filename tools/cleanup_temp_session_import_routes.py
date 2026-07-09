from pathlib import Path
import re

path = Path("app.py")
text = path.read_text(encoding="utf-8")

markers = [
    "NOVA_SESSION_IMPORT_TOKEN_ROUTE_20260703",
    "NOVA_ADMIN_SESSION_STORE_IMPORT",
    "session-store/import",
]

original = text

# Remove exact token route block.
text = re.sub(
    r'\n# === NOVA_SESSION_IMPORT_TOKEN_ROUTE_20260703 ===.*?(?=\n# === NOVA_|\Z)',
    "\n",
    text,
    flags=re.S,
)

# Remove any earlier temporary /api/admin/session-store/import route block if present.
text = re.sub(
    r'\n# === .*?SESSION.*?IMPORT.*? ===.*?/api/admin/session-store/import.*?(?=\n# === NOVA_|\Z)',
    "\n",
    text,
    flags=re.S | re.I,
)

# Fallback: warn if import route text still exists.
path.write_text(text.rstrip() + "\n", encoding="utf-8")

print("removed chars:", len(original) - len(text))
print("still has import-token:", "import-token" in text)
print("still has session-store/import:", "session-store/import" in text)
