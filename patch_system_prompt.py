from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
s = p.read_text(encoding="utf-8-sig")

anchor = "    def _build_working_state_summary(self, working_state):"
pos = s.find(anchor)
if pos == -1:
    raise SystemExit("ANCHOR NOT FOUND")

next_def = s.find("\n    def ", pos + 1)
if next_def == -1:
    raise SystemExit("NEXT DEF NOT FOUND")

insert = '''
    def _build_system_prompt(self, decision=None):
        parts = []

        parts.append(
            "You are Nova, a focused AI workspace assistant. "
            "Be clear, direct, continuity-aware, and useful. "
            "Prefer action over explanation. "
            "Do not ramble. "
            "Preserve the user's momentum."
        )

        route = ""
        if isinstance(decision, dict):
            route = str(decision.get("route") or decision.get("mode") or "").strip()

        if route:
            parts.append(f"Current route: {route}")

        return "\\n\\n".join(part for part in parts if str(part).strip())

'''

if "_build_system_prompt" not in s[:next_def]:
    s = s[:next_def] + insert + s[next_def:]

p.write_text(s, encoding="utf-8")
print("PATCHED_SYSTEM_PROMPT")
