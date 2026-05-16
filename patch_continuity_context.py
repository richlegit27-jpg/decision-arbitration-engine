from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
s = p.read_text(encoding="utf-8-sig")

anchor = "    def _compose_model_messages(self,"
pos = s.find(anchor)
if pos == -1:
    raise SystemExit("ANCHOR NOT FOUND")

insert = '''
    def _build_continuity_context(self, session=None):
        session = session or {}
        messages = session.get("messages") if isinstance(session, dict) else []
        if not isinstance(messages, list) or not messages:
            return ""

        recent = messages[-6:]
        lines = []

        for msg in recent:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role") or "").strip()
            text = str(msg.get("text") or msg.get("content") or "").strip()
            if role and text:
                lines.append(f"{role}: {text[:500]}")

        if not lines:
            return ""

        return "Recent conversation:\\n" + "\\n".join(lines)

'''

if "    def _build_continuity_context(self," not in s[:pos]:
    s = s[:pos] + insert + s[pos:]

p.write_text(s, encoding="utf-8")
print("PATCHED_CONTINUITY_CONTEXT")
