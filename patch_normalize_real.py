from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
s = p.read_text(encoding="utf-8-sig")

anchor = "    def _build_system_prompt(self, decision=None):"
pos = s.find(anchor)
if pos == -1:
    raise SystemExit("ANCHOR NOT FOUND")

insert = '''
    def _normalize_working_state(self, working_state):
        if isinstance(working_state, dict):
            return working_state
        if working_state is None:
            return {}
        if isinstance(working_state, str):
            try:
                import json
                parsed = json.loads(working_state)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

'''

s = s[:pos] + insert + s[pos:]

p.write_text(s, encoding="utf-8")
print("PATCHED_NORMALIZE_IN_REAL_CLASS")
