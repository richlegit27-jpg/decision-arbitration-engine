from pathlib import Path
import re

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="ignore")

marker = "# NOVA_FINAL_JUST_FIXED_PROJECT_STATE_RESPONSE_LOCK_20260702"

if marker not in text:
    raise SystemExit("marker not found in app.py")

# Extract the appended block.
start = text.find("\n" + marker)
if start == -1:
    start = text.find(marker)

block = text[start:].strip() + "\n"
without = text[:start].rstrip() + "\n"

# Insert before local app.run / __main__ so it executes before the server blocks.
main_match = re.search(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:\s*$', without)

if not main_match:
    raise SystemExit("could not find if __name__ == '__main__' block")

new_text = without[:main_match.start()].rstrip() + "\n\n" + block + "\n" + without[main_match.start():]

path.write_text(new_text, encoding="utf-8")
print("moved final just-fixed response lock above __main__/app.run")
