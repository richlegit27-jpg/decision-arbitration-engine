from pathlib import Path

path = Path("nova_backend/services/project_brain_general_intelligence.py")
text = path.read_text(encoding="utf-8")

start = text.index("def classify_project_brain_intent(user_text: object) -> Optional[str]:")
end = text.index("\n\ndef build_project_brain_general_answer", start)

new_func = r'''def classify_project_brain_intent(user_text: object) -> Optional[str]:
    text = _lower(user_text)

    if not text:
        return None

    if _is_direct_project_state_recall_prompt(text):
        return None

    if _has_any(text, ("attached", "image", "photo", "picture", "upload", "summarize this file")):
        return None

    project_terms = (
        "nova",
        "project",
        "app.py",
        "local app",
        "flask app",
        "codebase",
        "we",
    )

    status_terms = (
        "where are we",
        "where are we at",
        "where do we stand",
        "where's the project",
        "project at",
        "status",
        "state",
        "checkpoint",
        "current",
        "right now",
    )

    next_terms = (
        "next",
        "next move",
        "concrete move",
        "what now",
        "what should we do",
        "what do we do",
        "safe move",
        "practical move",
    )

    blocker_terms = (
        "blocker",
        "blocking",
        "stuck",
        "risk",
        "risky",
        "danger",
        "dangerous",
        "problem",
        "wrong",
    )

    safe_code_terms = (
        "safe to code",
        "safe to change",
        "before coding",
        "before we code",
        "before changing",
        "before we change",
        "before touching",
        "touch code",
        "change more code",
        "test first",
        "should we test",
        "safest next",
        "safest move",
        "safe next",
    )

    practical_terms = (
        "practical",
        "no hype",
        "without hype",
        "not a pep talk",
        "no pep talk",
        "straight answer",
        "real answer",
        "actual answer",
        "concrete",
    )

    memory_terms = (
        "memory",
        "remember",
        "remembers",
        "remembering",
        "retains",
        "stored",
        "knows",
        "know",
    )

    execution_terms = (
        "execution",
        "execute",
        "doing",
        "actively doing",
        "does",
        "do",
        "runs",
        "running",
        "actions",
        "commands",
        "patch",
        "live",
    )

    if "app.py" in text and _has_any(text, blocker_terms + ("architecture", "guard", "hooks", "route")):
        return "app_py_risk"

    if (
        _has_any(text, memory_terms)
        and _has_any(text, execution_terms)
        and _has_any(text, ("nova", "separate", "difference", "distinction", "versus", "vs", "what should", "what is"))
    ):
        return "memory_execution_distinction"

    if (
        _has_any(text, ("memory or execution", "remembering or doing", "know vs do", "knows vs does"))
        or (
            _has_any(text, ("what should nova know", "what nova should know", "what should nova remember"))
            and _has_any(text, ("do", "doing", "execute", "execution"))
        )
    ):
        return "memory_execution_distinction"

    if _has_any(text, safe_code_terms):
        return "safe_next_action"

    if (
        _has_any(text, practical_terms)
        and _has_any(text, project_terms + status_terms + next_terms)
    ):
        return "practical_project_answer"

    if (
        _has_any(text, blocker_terms)
        and _has_any(text, project_terms)
    ):
        if "app.py" in text:
            return "app_py_risk"
        return "current_project_state"

    if (
        _has_any(text, next_terms)
        and _has_any(text, project_terms + ("code", "work"))
    ):
        return "practical_project_answer"

    if (
        _has_any(text, status_terms)
        and _has_any(text, project_terms)
    ):
        return "current_project_state"

    return None
'''

text = text[:start] + new_func + text[end:]
path.write_text(text, encoding="utf-8")
print("broadened project brain classifier")
