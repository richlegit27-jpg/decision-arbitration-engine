from pathlib import Path
from datetime import datetime
import re

path = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
text = path.read_text(encoding="utf-8")

# Backup
backup = path.with_suffix(path.suffix + f".BAK_attachment_helper_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
backup.write_text(text, encoding="utf-8")
print(f"Backup saved at {backup}")

# 1. Insert helper function at the top after imports
helper_func = '''
def _build_attachment_analysis(attachments, topic_lines):
    if not attachments:
        return ""
    reply = "Attachment analysis:\\n"
    reply += f"This attachment appears to contain extracted image/PDF content about: {'; '.join(topic_lines[:3])}\\n\\n"
    reply += "Key points:\\n"
    for i, line in enumerate(topic_lines, start=1):
        reply += f"{i}. {line}\\n"
    reply += "\\nPreview:\\n" + "\\n".join(topic_lines[:6])
    return reply
'''

if "_build_attachment_analysis" not in text:
    # insert after first import block (roughly)
    import_end = text.find("\n\n") + 2
    text = text[:import_end] + helper_func + "\n" + text[import_end:]

# 2. Replace _reply and _nova_reply attachment analysis blocks with helper call
patterns = [
    r'_reply\s*=\s*"(Attachment analysis:.*)"',
    r'_nova_reply\s*=\s*"(Attachment analysis:.*)"',
    r'reply\s*=\s*"(Attachment analysis:.*)"'
]

for pat in patterns:
    text = re.sub(pat, "_reply = _build_attachment_analysis(attachments, top)", text)
    text = re.sub(pat, "_nova_reply = _build_attachment_analysis(attachments, _nova_top)", text)

# 3. Save patched file
path.write_text(text, encoding="utf-8")
print("OK: attachment analysis wrapped in helper.")
print(f"FILE: {path}")