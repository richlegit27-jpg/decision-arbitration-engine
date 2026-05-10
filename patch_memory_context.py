from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
s = p.read_text(encoding="utf-8-sig")

anchor = "    def _build_system_prompt(self, decision=None):"
pos = s.find(anchor)
if pos == -1:
    raise SystemExit("ANCHOR NOT FOUND")

insert = '''
    def _build_memory_context_for_chat(self, user_text="", decision=None):
        try:
            memory_context = getattr(self, "memory_context", "")
            if memory_context:
                return str(memory_context)
        except Exception:
            pass
        return ""

'''

if "    def _build_memory_context_for_chat(self," not in s[:pos]:
    s = s[:pos] + insert + s[pos:]

p.write_text(s, encoding="utf-8")
print("PATCHED_MEMORY_CONTEXT_FOR_CHAT")
