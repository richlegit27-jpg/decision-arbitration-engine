from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
s = p.read_text(encoding="utf-8-sig")

anchor = "    def _update_working_state(self, session_id: str, patch: dict) -> dict:"
pos = s.find(anchor)
if pos == -1:
    raise SystemExit("ANCHOR NOT FOUND")

next_def = s.find("\n    def ", pos + 1)
if next_def == -1:
    raise SystemExit("NEXT DEF NOT FOUND")

insert = '''
    def _build_working_state_summary(self, working_state):
        ws = self._normalize_working_state(working_state)
        if not ws:
            return ""

        lines = []
        mapping = [
            ("active_task", "Active task"),
            ("current_file", "Current file"),
            ("current_bug", "Current bug"),
            ("last_success", "Last success"),
            ("next_move", "Next move"),
            ("checkpoint", "Checkpoint"),
        ]

        for key, label in mapping:
            value = str(ws.get(key, "")).strip()
            if value:
                lines.append(f"{label}: {value}")

        if not lines:
            return ""

        return "Working context:\\n" + "\\n".join(lines)

'''

if "_build_working_state_summary" not in s[:next_def]:
    s = s[:next_def] + insert + s[next_def:]

p.write_text(s, encoding="utf-8")
print("PATCHED")
