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
    from nova_backend.services.project_brain_live_answer_selector import build_project_brain_live_answer

    return build_project_brain_live_answer(user_text=user_text).text

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


# NOVA_PROJECT_BRAIN_MISSION_CONTROL_GENERAL_20260702
# Service-only Mission Control answer bridge.
# No Flask wiring and no app.py dependency.
def _mission_control_answer(user_text: object) -> str:
    from nova_backend.services.project_brain_mission_control import (
        build_project_brain_mission_control_answer,
    )

    return build_project_brain_mission_control_answer(
        user_text=str(user_text or ""),
        pasted_output="",
    )

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

    mission_terms = (
        "mission control",
        "mission card",
        "operator mode",
        "operator card",
        "mission brief",
        "mission plan",
        "give me mission",
        "show mission",
        "show me the mission",
    )

    if _has_any(text, mission_terms):
        return "mission_control"

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

    if intent == "mission_control":
        return ProjectBrainAnswer(intent=intent, text=_mission_control_answer(user_text))

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

# NOVA_PROJECT_BRAIN_GENERAL_LIVE_SELECTOR_CLASSIFIER_20260702
# Broadens Project Brain general question detection so live selector can win
# before stale compact project_state_context fallback handles paraphrases.
try:
    _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_CLASSIFIER_20260702 = should_handle_project_brain_general_question

    def _nova_project_brain_live_selector_general_phrase_20260702(user_text):
        q = str(user_text or "").strip().lower()
        q = " ".join(q.replace("?", " ").replace("!", " ").split())

        exact_direct_project_state = {
            "what are we working on",
            "what are we working on now",
            "what are we working on right now",
        }
        if q in exact_direct_project_state:
            return False

        phrases = [
            "where are we at with nova right now",
            "where are we at with nova",
            "where are we at",
            "where is nova at",
            "where's nova at",
            "where is the project at",
            "where's the project at",
            "give me the nova status",
            "nova status without hype",
            "what should we do next",
            "what should we do",
            "what's next",
            "next concrete move",
            "next move",
            "what now",
            "should we patch app.py",
            "should we patch or test",
            "should we test first",
            "test first",
            "safe to code",
            "what test should we run",
            "what does this failure mean",
            "why did this fail",
            "stale memory",
            "memory hijacking",
        ]

        return any(phrase in q for phrase in phrases)

    def should_handle_project_brain_general_question(user_text):
        q = str(user_text or "").strip().lower()
        q = " ".join(q.replace("?", " ").replace("!", " ").split())

        if q in {
            "what are we working on",
            "what are we working on now",
            "what are we working on right now",
        }:
            return False

        if _nova_project_brain_live_selector_general_phrase_20260702(user_text):
            return True

        return _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_CLASSIFIER_20260702(user_text)

except Exception as _nova_project_brain_general_live_selector_classifier_error_20260702:
    pass

# NOVA_PROJECT_BRAIN_GENERAL_LIVE_SELECTOR_EXPORTED_CLASSIFIER_20260702
# Exports a stable Project Brain general classifier and routes matched questions
# through the live answer selector. Service-only. No app.py changes.
try:
    _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_BUILD_20260702 = build_project_brain_general_answer
except Exception:
    _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_BUILD_20260702 = None


def _nova_project_brain_general_live_selector_normalize_20260702(user_text):
    q = str(user_text or "").strip().lower()
    q = q.replace("?", " ").replace("!", " ").replace(".", " ")
    q = " ".join(q.split())
    return q


def should_handle_project_brain_general_question(user_text):
    q = _nova_project_brain_general_live_selector_normalize_20260702(user_text)

    exact_direct_project_state = {
        "what are we working on",
        "what are we working on now",
        "what are we working on right now",
    }
    if q in exact_direct_project_state:
        return False

    phrases = [
        "where are we at with nova right now",
        "where are we at with nova",
        "where are we at",
        "where is nova at",
        "where's nova at",
        "where is the project at",
        "where's the project at",
        "give me the nova status",
        "nova status without hype",
        "what should we do next",
        "what should we do",
        "what's next",
        "next concrete move",
        "next move",
        "what now",
        "should we patch app py",
        "should we patch app.py",
        "should we patch or test",
        "should we test first",
        "test first",
        "safe to code",
        "what test should we run",
        "what does this failure mean",
        "why did this fail",
        "stale memory",
        "memory hijacking",
        "source of truth",
    ]

    return any(phrase in q for phrase in phrases)


def _nova_project_brain_command_center_question_20260702(user_text):
    q = _nova_project_brain_general_live_selector_normalize_20260702(user_text)

    exact_direct_project_state = {
        "what are we working on",
        "what are we working on now",
        "what are we working on right now",
    }
    if q in exact_direct_project_state:
        return False

    phrases = [
        "command center",
        "project brain command center",
        "operator dashboard",
        "what smoke should we run",
        "which smoke should we run",
        "what test should we run",
        "which test should we run",
        "run checks",
        "validation",
        "what failed",
        "what does this failure mean",
        "why did this fail",
        "recent changes",
        "recent decisions",
        "decision log",
        "what changed recently",
        "what did we lock recently",
        "what got locked recently",
        "next upgrade",
        "next gangster upgrade",
        "gangster upgrade",
    ]

    if any(phrase in q for phrase in phrases):
        return True

    if q in {
        "status",
        "project status",
        "nova status",
        "current status",
        "current blocker",
        "next",
        "next move",
    }:
        return True

    return False


def build_project_brain_general_answer(user_text=""):
    q = _nova_project_brain_general_live_selector_normalize_20260702(user_text)

    if q in {
        "what are we working on",
        "what are we working on now",
        "what are we working on right now",
    }:
        return None

    if _nova_project_brain_command_center_question_20260702(user_text):
        from nova_backend.services.project_brain_command_center import (
            build_project_brain_command_center_answer,
        )

        return ProjectBrainAnswer(
            intent="command_center",
            text=build_project_brain_command_center_answer(
                user_text=str(user_text or ""),
                pasted_output="",
                changed_files=None,
            ),
        )

    if should_handle_project_brain_general_question(user_text):
        from nova_backend.services.project_brain_live_answer_selector import (
            build_project_brain_live_answer,
        )

        return build_project_brain_live_answer(user_text=user_text).text

    if callable(_NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_BUILD_20260702):
        return _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_BUILD_20260702(user_text)

    return None



# NOVA_PROJECT_BRAIN_DECISION_LOG_GENERAL_WIRE_20260701
# Routes recent-change/operator-timeline questions through the Git-backed
# Decision Log service while preserving direct project-state recall.
try:
    from nova_backend.services.project_brain_decision_log import answer_recent_changes as _nova_decision_log_answer_20260701

    _NOVA_DECISION_LOG_PREVIOUS__CURRENT_PROJECT_ANSWER_20260701 = _current_project_answer

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

    def _current_project_answer(*args, **kwargs):
        user_text = _nova_decision_log_user_text_20260701(*args, **kwargs)

        if _nova_is_decision_log_question_20260701(user_text):
            return {
                "intent": "decision_log",
                "answer": _nova_decision_log_answer_20260701(limit=8),
                "route": "project_brain_general_intelligence",
                "risk": "low",
                "confidence": 0.91,
            }

        return _NOVA_DECISION_LOG_PREVIOUS__CURRENT_PROJECT_ANSWER_20260701(*args, **kwargs)

    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_GENERAL_WIRE_20260701] installed on _current_project_answer")
except Exception as _nova_decision_log_wire_error_20260701:
    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_GENERAL_WIRE_20260701] failed:", _nova_decision_log_wire_error_20260701)
