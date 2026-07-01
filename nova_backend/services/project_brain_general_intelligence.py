from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProjectBrainAnswer:
    intent: str
    text: str


def _clean(value: object) -> str:
    return str(value or "").strip()


def _lower(value: object) -> str:
    return _clean(value).lower()


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _current_project_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_current_project_answer

    return build_current_project_answer()

def _safe_next_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_safe_next_answer

    return build_safe_next_answer()

def _memory_execution_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_memory_execution_answer

    return build_memory_execution_answer()

def _app_py_risk_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_app_py_risk_answer

    return build_app_py_risk_answer()

def _practical_project_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_practical_project_answer

    return build_practical_project_answer()

def _is_direct_project_state_recall_prompt(text: str) -> bool:
    normalized = " ".join(text.replace("?", " ").replace("!", " ").split())

    direct_prompts = {
        "what are we working on now",
        "what are we working on",
        "what are we working on right now",
    }

    return normalized in direct_prompts


def classify_project_brain_intent(user_text: object) -> Optional[str]:
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
        and _has_any(
            text,
            (
                "nova",
                "separate",
                "difference",
                "distinction",
                "versus",
                "vs",
                "what should",
                "what is",
                "problem",
                "issue",
                "this a",
                "is this",
            ),
        )
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


def build_project_brain_general_answer(user_text: object) -> Optional[ProjectBrainAnswer]:
    intent = classify_project_brain_intent(user_text)

    if intent == "current_project_state":
        return ProjectBrainAnswer(intent=intent, text=_current_project_answer())

    if intent == "safe_next_action":
        return ProjectBrainAnswer(intent=intent, text=_safe_next_answer())

    if intent == "memory_execution_distinction":
        return ProjectBrainAnswer(intent=intent, text=_memory_execution_answer())

    if intent == "app_py_risk":
        return ProjectBrainAnswer(intent=intent, text=_app_py_risk_answer())

    if intent == "practical_project_answer":
        return ProjectBrainAnswer(intent=intent, text=_practical_project_answer())

    return None
