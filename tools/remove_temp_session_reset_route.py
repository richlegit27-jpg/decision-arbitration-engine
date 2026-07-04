from pathlib import Path
import re

path = Path("app.py")
text = path.read_text(encoding="utf-8")

pattern = r'\n# NOVA_TEMP_SESSION_RESET_ROUTE_20260704\n@app\.post\("/api/admin/reset-sessions-clean-start"\)\ndef nova_temp_reset_sessions_clean_start_20260704\(\):\n(?:    .*\n)+?(?=\n\nif __name__ == "__main__"|\n\n@app\.|\Z)'

new_text, count = re.subn(pattern, "\n", text, count=1)

if count == 0:
    raise SystemExit("Reset route block not found.")

path.write_text(new_text, encoding="utf-8")
print("Removed temporary reset route.")
