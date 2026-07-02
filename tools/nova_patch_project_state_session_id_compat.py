from pathlib import Path
import re

ROOTS = [
    Path("app.py"),
    Path("nova_backend"),
]

def iter_py_files():
    for root in ROOTS:
        if root.is_file() and root.suffix == ".py":
            yield root
        elif root.is_dir():
            yield from root.rglob("*.py")

targets = []
for path in iter_py_files():
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "def answer_project_state_question" in text:
        targets.append(path)

if not targets:
    raise SystemExit("Could not find def answer_project_state_question")

changed = []

for path in targets:
    text = path.read_text(encoding="utf-8", errors="ignore")
    original = text

    # Match the function header even if it spans one line.
    pattern = re.compile(r"def\s+answer_project_state_question\s*\(([^)]*)\):")

    def repl(match):
        args = match.group(1).strip()

        if "session_id" in args or "**kwargs" in args:
            return match.group(0)

        if not args:
            new_args = "session_id=None, **kwargs"
        else:
            new_args = args + ", session_id=None, **kwargs"

        return f"def answer_project_state_question({new_args}):"

    text = pattern.sub(repl, text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        changed.append(str(path))

print("patched files:")
for item in changed:
    print("-", item)

if not changed:
    print("No change needed; function already accepts session_id or kwargs.")
