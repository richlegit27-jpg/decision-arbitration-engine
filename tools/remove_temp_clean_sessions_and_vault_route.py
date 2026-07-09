from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

start_marker = "# NOVA_TEMP_CLEAN_SESSIONS_AND_VAULT_ROUTE_20260704_BEGIN"
end_marker = "# NOVA_TEMP_CLEAN_SESSIONS_AND_VAULT_ROUTE_20260704_END"

start = text.find(start_marker)
end = text.find(end_marker)

if start == -1 or end == -1:
    raise SystemExit("Temp clean sessions+vault route markers not found.")

end = end + len(end_marker)

new_text = text[:start].rstrip() + "\n\n" + text[end:].lstrip()

path.write_text(new_text, encoding="utf-8")

print("Removed temp clean sessions+vault route.")
