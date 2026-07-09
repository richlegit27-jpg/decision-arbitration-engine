from pathlib import Path
import re


TARGET = Path("app.py")
MARKER = "NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701"

if not TARGET.exists():
    raise SystemExit("missing app.py")

text = TARGET.read_text(encoding="utf-8-sig")

start = text.find(f"# {MARKER}")
if start < 0:
    raise SystemExit("Decision Log API route contract block not found in app.py")

pattern = re.compile(
    r"\n*# NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701"
    r".*?"
    r"print\(\s*\"\[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701\] failed:\",\s*_nova_decision_log_api_route_error_20260701\s*\)\n?",
    re.DOTALL,
)

match = pattern.search(text)
if not match:
    raise SystemExit("could not isolate Decision Log API route contract block")

block = match.group(0).strip() + "\n\n"

text_without_block = text[:match.start()] + "\n" + text[match.end():]

anchors = [
    '\nif __name__ == "__main__":',
    "\nif __name__ == '__main__':",
    "\napp.run(",
]

insert_at = -1
anchor_used = ""

for anchor in anchors:
    index = text_without_block.rfind(anchor)
    if index >= 0:
        insert_at = index
        anchor_used = anchor.strip()
        break

if insert_at < 0:
    raise SystemExit("could not find app boot anchor to insert route contract before")

new_text = (
    text_without_block[:insert_at].rstrip()
    + "\n\n"
    + block
    + text_without_block[insert_at:].lstrip()
)

TARGET.write_text(new_text, encoding="utf-8")

print(f"moved Decision Log API route contract before {anchor_used}")
