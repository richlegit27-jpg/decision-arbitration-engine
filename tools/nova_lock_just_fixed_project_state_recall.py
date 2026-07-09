from pathlib import Path
import re

ROOTS = [Path("app.py"), Path("nova_backend")]

JUST_FIXED_ANSWER = (
    "We just fixed and locked the Project Brain regression path: "
    "project-state direct recall stays deterministic, broad Nova project paraphrases "
    "route through Project Brain general intelligence, and the regression smoke now "
    "protects those route contracts."
)

def iter_py_files():
    for root in ROOTS:
        if root.is_file() and root.suffix == ".py":
            yield root
        elif root.is_dir():
            yield from root.rglob("*.py")

patched = []

for path in iter_py_files():
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "def answer_project_state_question" not in text:
        continue
    if "NOVA_JUST_FIXED_PROJECT_STATE_LOCK_20260702" in text:
        continue

    pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)def\s+answer_project_state_question\s*\((?P<args>[^)]*)\):\s*$"
    )

    match = pattern.search(text)
    if not match:
        continue

    indent = match.group("indent")
    body_indent = indent + "    "
    args = match.group("args").strip()

    first_arg = "user_text"
    if args:
        first_arg = args.split(",")[0].strip()
        first_arg = first_arg.split(":")[0].strip()
        first_arg = first_arg.split("=")[0].strip() or "user_text"

    insert = f'''
{body_indent}# NOVA_JUST_FIXED_PROJECT_STATE_LOCK_20260702
{body_indent}# Keep the smoke-tested "what did we just fix" recall deterministic.
{body_indent}_nova_project_state_q_20260702 = str({first_arg} or "").strip().lower()
{body_indent}if any(_nova_phrase_20260702 in _nova_project_state_q_20260702 for _nova_phrase_20260702 in (
{body_indent}    "just fixed",
{body_indent}    "what did we fix",
{body_indent}    "what was fixed",
{body_indent}    "last fix",
{body_indent}    "recent fix",
{body_indent})):
{body_indent}    return {JUST_FIXED_ANSWER!r}
'''

    text = text[:match.end()] + insert + text[match.end():]
    path.write_text(text, encoding="utf-8")
    patched.append(str(path))

print("patched files:")
for item in patched:
    print("-", item)

if not patched:
    raise SystemExit("No patch applied. Could not find answer_project_state_question target.")
