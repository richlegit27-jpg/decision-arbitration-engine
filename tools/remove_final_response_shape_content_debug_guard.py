from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8-sig")

start_marker = "# NOVA_FINAL_RESPONSE_SHAPE_CONTENT_DEBUG_20260701"
end_marker = "# NOVA_API_CHAT_PROJECT_NEXT_FINAL_OVERRIDE_20260701"

start = text.find(start_marker)
if start == -1:
    raise SystemExit("start marker not found")

if start > 0 and text[start - 1] == "\n":
    start = start - 1

end = text.find(end_marker, start)
if end == -1:
    raise SystemExit("end marker not found")

new_text = text[:start].rstrip() + "\n\n" + text[end:].lstrip()

APP.write_text(new_text, encoding="utf-8")
print("removed NOVA_FINAL_RESPONSE_SHAPE_CONTENT_DEBUG_20260701 block")
