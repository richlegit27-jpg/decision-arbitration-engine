from pathlib import Path
import ast


TARGET = Path("nova_backend/services/project_brain_general_intelligence.py")
MARKER = "NOVA_PROJECT_BRAIN_DECISION_LOG_GENERAL_WIRE_20260701"

if not TARGET.exists():
    raise SystemExit(f"missing target file: {TARGET}")

text = TARGET.read_text(encoding="utf-8-sig")

if MARKER in text:
    print("Decision Log general-intelligence wire already installed")
    raise SystemExit(0)


def find_handler_name(source: str) -> str:
    tree = ast.parse(source)

    function_names = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    ]

    preferred = [
        "answer_project_brain_question",
        "answer_project_brain_general_intelligence",
        "answer_general_intelligence",
        "handle_project_brain_question",
        "handle_general_intelligence",
        "build_project_brain_answer",
        "classify_and_answer_project_brain",
    ]

    for name in preferred:
        if name in function_names:
            return name

    for name in function_names:
        lowered = name.lower()
        if "answer" in lowered and ("project" in lowered or "brain" in lowered or "general" in lowered):
            return name

    for name in function_names:
        lowered = name.lower()
        if "handle" in lowered and ("project" in lowered or "brain" in lowered or "general" in lowered):
            return name

    raise SystemExit(
        "could not find Project Brain general-intelligence answer handler. "
        f"functions found={function_names}"
    )


handler = find_handler_name(text)

wire = f'''


# {MARKER}
# Routes recent-change/operator-timeline questions through the Git-backed
# Decision Log service while preserving direct project-state recall.
try:
    from nova_backend.services.project_brain_decision_log import answer_recent_changes as _nova_decision_log_answer_20260701

    _NOVA_DECISION_LOG_PREVIOUS_{handler.upper()}_20260701 = {handler}

    def _nova_decision_log_user_text_20260701(*args, **kwargs):
        if args:
            first = args[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for key in ("message", "question", "user_text", "text", "prompt"):
                    value = first.get(key)
                    if isinstance(value, str):
                        return value

        for key in ("message", "question", "user_text", "text", "prompt"):
            value = kwargs.get(key)
            if isinstance(value, str):
                return value

        return ""

    def _nova_is_decision_log_question_20260701(user_text):
        text = str(user_text or "").strip().lower()
        if not text:
            return False

        needles = (
            "what changed recently",
            "what changed lately",
            "recent changes",
            "recent decisions",
            "decision log",
            "recent commits",
            "last commits",
            "latest commits",
            "what did we commit",
            "what did we lock recently",
            "what got locked recently",
            "locked upgrades",
            "operator timeline",
            "what changed in project brain",
            "what changed with project brain",
        )

        return any(needle in text for needle in needles)

    def {handler}(*args, **kwargs):
        user_text = _nova_decision_log_user_text_20260701(*args, **kwargs)

        if _nova_is_decision_log_question_20260701(user_text):
            return {{
                "intent": "decision_log",
                "answer": _nova_decision_log_answer_20260701(limit=8),
                "route": "project_brain_general_intelligence",
                "risk": "low",
                "confidence": 0.91,
            }}

        return _NOVA_DECISION_LOG_PREVIOUS_{handler.upper()}_20260701(*args, **kwargs)

    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_GENERAL_WIRE_20260701] installed on {handler}")
except Exception as _nova_decision_log_wire_error_20260701:
    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_GENERAL_WIRE_20260701] failed:", _nova_decision_log_wire_error_20260701)
'''

TARGET.write_text(text + wire, encoding="utf-8")
print(f"patched {TARGET} using handler {handler}")
