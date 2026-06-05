from pathlib import Path
from datetime import datetime

# Path to your live chat_service.py
path = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")

# Backup first
backup = path.with_suffix(path.suffix + f".BAK_surgical_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
print(f"Backup saved at {backup}")

text = path.read_text(encoding="utf-8")

# 1. Insert helper function _build_attachment_analysis at the top of chat_service.py (after imports)
helper_func = '''
def _build_attachment_analysis(attachments, session_id):
    if not attachments:
        return ""
    _reply = "Attachment analysis:\\n"
    for att in attachments:
        try:
            path_candidate = att.get("file_url") or att.get("url") or ""
            _reply += f"This attachment appears to contain extracted image/PDF content about: {path_candidate}\\n"
        except Exception:
            continue
    return _reply
'''

if "_build_attachment_analysis" not in text:
    # insert after the first import block
    import_end_idx = text.find("from")  # rough approximation
    text = text[:import_end_idx] + helper_func + "\n" + text[import_end_idx:]

# 2. Replace all literal "Attachment analysis:" builders with call to helper function
# matches _reply = "Attachment analysis:...
import re
pattern = r'_reply\s*=\s*"(Attachment analysis:.*)"'
text = re.sub(pattern, "_reply = _build_attachment_analysis(attachments, session_id)", text)

# 3. Also replace any other literal occurrences (like reply = "Attachment analysis:")
pattern2 = r'reply\s*=\s*"(Attachment analysis:.*)"'
text = re.sub(pattern2, "reply = _build_attachment_analysis(attachments, session_id)", text)

# Save fixed file
path.write_text(text, encoding="utf-8")
print("OK: surgical attachment analysis fix applied.")
print(f"FILE: {path}")