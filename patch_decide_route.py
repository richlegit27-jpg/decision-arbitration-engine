from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
s = p.read_text(encoding="utf-8-sig")

anchor = "    def _build_system_prompt(self, decision=None):"
pos = s.find(anchor)
if pos == -1:
    raise SystemExit("ANCHOR NOT FOUND")

insert = '''
    def _decide_route(self, user_text="", attachments=None, memory_context="", working_context_block="", session_id=""):
        return {
            "route": self.ROUTE_GENERAL_CHAT,
            "mode": "chat",
            "confidence": 0.6,
            "reasons": ["fallback_decide_route"],
            "save_artifact": False,
            "save_memory": True,
            "use_memory": True,
        }

'''

if "    def _decide_route(self," not in s[:pos]:
    s = s[:pos] + insert + s[pos:]

p.write_text(s, encoding="utf-8")
print("PATCHED_DECIDE_ROUTE")
