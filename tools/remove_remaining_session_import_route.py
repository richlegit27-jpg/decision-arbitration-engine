from pathlib import Path

path = Path("app.py")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

out = []
i = 0
removed = 0

while i < len(lines):
    line = lines[i]

    if (
        '@app.post("/api/admin/session-store/import")' in line
        or "@app.post('/api/admin/session-store/import')" in line
        or '@app.route("/api/admin/session-store/import"' in line
        or "@app.route('/api/admin/session-store/import'" in line
    ):
        removed += 1
        i += 1

        # Also remove the following function body.
        if i < len(lines) and "def nova_richard_session_store_import_20260703" in lines[i]:
            i += 1

            while i < len(lines):
                current = lines[i]

                # Stop when we hit the next top-level or next 4-space block after the route function.
                if current.startswith("except ") or current.startswith("# === "):
                    break

                if current.startswith("    ") and not current.startswith("        ") and current.strip():
                    # Usually the install print after the route.
                    break

                i += 1

        continue

    out.append(line)
    i += 1

path.write_text("".join(out).rstrip() + "\n", encoding="utf-8")

text = path.read_text(encoding="utf-8")
print("removed route decorators:", removed)
print("still has /api/admin/session-store/import:", "/api/admin/session-store/import" in text)
print("still has import-token:", "import-token" in text)
