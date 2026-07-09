from pathlib import Path
import re

# Fix accidental unindented body after answer_project_state_question.
path = Path("nova_backend/services/project_state_service.py")
lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

def_idx = None
for i, line in enumerate(lines):
    if re.match(r"^\s*def\s+answer_project_state_question\s*\(", line):
        def_idx = i
        break

if def_idx is None:
    raise SystemExit("answer_project_state_question not found")

def_indent = len(lines[def_idx]) - len(lines[def_idx].lstrip())
body_indent = " " * (def_indent + 4)

end_idx = len(lines)
for j in range(def_idx + 1, len(lines)):
    stripped = lines[j].lstrip()
    indent = len(lines[j]) - len(stripped)
    if stripped and indent <= def_indent and re.match(r"(def|class)\s+", stripped):
        end_idx = j
        break

for j in range(def_idx + 1, end_idx):
    line = lines[j]
    stripped = line.lstrip()
    if not stripped:
        continue
    indent = len(line) - len(stripped)
    if indent <= def_indent:
        lines[j] = body_indent + stripped

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("repaired project_state_service answer_project_state_question indentation")
