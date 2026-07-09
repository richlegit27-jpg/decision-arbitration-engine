from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8-sig")

start_marker = "# NOVA_ATTACHMENT_FINAL_RAW_JSON_RESPONSE_SYNC_20260611"
end_marker = "# NOVA_WEB_FETCH_REQUESTED_SESSION_BRIDGE_SAFE_20260612"

start = text.find(start_marker)
if start == -1:
    raise SystemExit("start marker not found")

if start > 0 and text[start - 1] == "\n":
    start = start - 1

end = text.find(end_marker, start)
if end == -1:
    raise SystemExit("end marker not found")

APP.write_text(text[:start].rstrip() + "\n\n" + text[end:].lstrip(), encoding="utf-8")
print("removed NOVA_ATTACHMENT_FINAL_RAW_JSON_RESPONSE_SYNC_20260611 block")
