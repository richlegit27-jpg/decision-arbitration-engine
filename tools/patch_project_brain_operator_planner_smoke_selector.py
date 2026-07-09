from pathlib import Path
import re


TARGET = Path("nova_backend/services/project_brain_operator_planner.py")

if not TARGET.exists():
    raise SystemExit("missing operator planner service")

text = TARGET.read_text(encoding="utf-8-sig")

if "project_brain_smoke_selector" in text and "select_focused_smokes" in text:
    print("Operator Planner already delegates to Smoke Selector")
    raise SystemExit(0)

pattern = re.compile(
    r"\n\ndef select_smokes\(work_type: str, changed_files: list\[str\] \| None = None\) -> list\[str\]:"
    r".*?"
    r"\n\ndef choose_recommended_move\(work_type: str\)",
    re.DOTALL,
)

match = pattern.search(text)
if not match:
    raise SystemExit("could not isolate select_smokes function")

replacement = r'''

def _operator_planner_smoke_work_type(work_type: str) -> str:
    text = normalize_text(work_type)

    if text == "operator_planning":
        return "operator_planner"

    if text == "smoke_selection":
        return "smoke_selector"

    return text


def select_smokes(work_type: str, changed_files: list[str] | None = None) -> list[str]:
    from nova_backend.services.project_brain_smoke_selector import (
        select_focused_smokes,
    )

    return select_focused_smokes(
        work_type=_operator_planner_smoke_work_type(work_type),
        changed_files=changed_files,
    )


def choose_recommended_move(work_type: str)'''

text = text[:match.start()] + replacement + text[match.end():]

TARGET.write_text(text, encoding="utf-8")

print("patched Operator Planner to delegate smoke selection to Smoke Selector")
