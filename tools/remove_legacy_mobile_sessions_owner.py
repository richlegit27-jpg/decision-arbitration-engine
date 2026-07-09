from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

marker = 'NOVA_MOBILE_UNIQUE_FINAL_SESSIONS_PANEL_OWNER_20260625'

if marker not in text:
    print("legacy sessions owner already absent")
    raise SystemExit(0)

marker_index = text.index(marker)

script_start = text.rfind("<script", 0, marker_index)
if script_start < 0:
    raise SystemExit("could not find script start before legacy sessions owner")

script_end = text.find("</script>", marker_index)
if script_end < 0:
    raise SystemExit("could not find script end after legacy sessions owner")

script_end = script_end + len("</script>")

comment = "<!-- /NOVA_MOBILE_UNIQUE_FINAL_SESSIONS_PANEL_OWNER_20260625 -->"
after = text[script_end:]
if after.lstrip().startswith(comment):
    leading_ws_len = len(after) - len(after.lstrip())
    script_end = script_end + leading_ws_len + len(comment)

removed = text[script_start:script_end]

if "window.switchSession(session.id)" not in removed:
    print("warning: removed legacy block did not contain expected broken switchSession line")

new_text = text[:script_start].rstrip() + "\n\n" + text[script_end:].lstrip()

path.write_text(new_text.rstrip() + "\n", encoding="utf-8")

print("removed legacy sessions owner block")
print("removed chars:", len(removed))
