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

def classify_project_brain_intent(user_text: object) -> Optional[str]:
    text = _lower(user_text)

    if not text:
        return None

    if _has_any(
        text,
        (
            "memory",
            "execution",
            "difference between memory and execution",
            "memory vs execution",
            "what nova remembers",
            "what nova is actively doing",
            "separate what nova remembers",
            "remembered from active",
        ),
    ):
        return "memory_execution_distinction"

    if _has_any(
        text,
        (
            "where are we at",
            "where are we at with nova",
            "where are we at with nova right now",
            "where is nova at",
            "current project",
            "project status",
        ),
    ):
        return "current_project_state"

    if _has_any(
        text,
        (
            "what should we do next",
            "what do we do next",
            "next move",
            "safest next",
            "safe next",
            "what test should we run",
            "which test should we run",
            "should we test first",
            "test first",
            "safe to code",
            "should we patch or test",
        ),
    ):
        return "safe_next_action"

    if _has_any(
        text,
        (
            "blocker",
            "blocking",
            "stuck",
            "current blocker",
        ),
    ):
        return "actual_blocker"

    return None

def _current_project_answer(
    user_text=""
) -> str:
    from nova_backend.services.project_brain_live_answer_selector import (
        build_project_brain_live_answer
    )

    return build_project_brain_live_answer(
        user_text=user_text
    ).text



def _safe_next_answer() -> str:
    from nova_backend.services.project_brain_context_builder import (
        build_project_brain_decision_context_answer,
    )

    return build_project_brain_decision_context_answer(
        user_text="what should we do next",
        intent="next_move",
    )

def _memory_execution_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_memory_execution_answer

    return build_memory_execution_answer()

def _app_py_risk_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_app_py_risk_answer

    return build_app_py_risk_answer()

def _practical_project_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_practical_project_answer

    return build_practical_project_answer()

def _append_behavior_context(answer: str) -> str:
    behavior_context = _behavior_context_answer()

    if not behavior_context:
        return answer

    improvement_lines = []

    for item in behavior_context.split("\n"):

        if "Current Nova improvement focus:" in item:

            improvement_lines.append(
                item
            )


    if improvement_lines:

        return (
            answer
            + "\n\nBehavior guidance:\n"
            + behavior_context
            + "\n\nRecommended improvement awareness:\n"
            + "\n".join(
                improvement_lines
            )
        )


    return (
        answer
        + "\n\nBehavior guidance:\n"
        + behavior_context
    )

def _behavior_context_answer() -> str:
    from nova_backend.services.nova_behavior_context_service import (
        build_behavior_context,
    )

    patterns = build_behavior_context()

    if not patterns:
        return ""

    return "\n".join(
        f"- {item}"
        for item in patterns
    )


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
        "where are we at with nova",
        "where are we at with nova right now",
        "where is nova at",
        "where is nova at right now",
    }

    return normalized in direct_prompts


    if _is_direct_project_state_recall_prompt(text):
        return "current_project_state"

    locked_terms = (
        "what is locked",
        "what's locked",
        "what got locked",
        "what did we lock",
        "locked stack",
        "locked upgrades",
        "what passed",
        "what is green",
        "what's green",
    )

    if _has_any(text, locked_terms):
        return "locked_state"

    if _has_any(text, ("attached", "image", "photo", "picture", "upload", "summarize this file")):
        return None

def _observe_project_brain_answer(
    user_text,
    answer_text,
):

    print(
        "[NOVA BEHAVIOR OBSERVE HIT]",
        user_text,
    )

    try:
        from nova_backend.services.nova_behavior_signal_builder import (
            behavior_signal_builder,
        )

        from nova_backend.services.nova_behavior_observer import (
            behavior_observer,
        )

        evaluation = behavior_signal_builder.build(
            user_text=str(user_text or ""),
            assistant_text=str(answer_text or ""),
            context="project_brain",
        )

        behavior_observer.observe(
            evaluation
        )

    except Exception as exc:
        print(
            "[NOVA_PROJECT_BRAIN_BEHAVIOR_FAILED]",
            exc,
        )

def _legacy_build_project_brain_general_answer_initial(user_text: object) -> Optional[ProjectBrainAnswer]:
    intent = classify_project_brain_intent(user_text)

    if intent == "locked_state":
        return ProjectBrainAnswer(
            intent="locked_state",
            text=_current_project_answer(user_text),
        )

    if intent == "mission_control":
        answer = _mission_control_answer(user_text)

        answer = _append_behavior_context(answer)

        _observe_project_brain_answer(
            user_text,
            answer,
        )

        return ProjectBrainAnswer(
            intent=intent,
            text=answer,
        )


    if intent == "current_project_state":
        answer = _current_project_answer()

        answer = _append_behavior_context(answer)

        _observe_project_brain_answer(
            user_text,
            answer,
        )

        return ProjectBrainAnswer(
            intent=intent,
            text=answer,
        )

    if intent == "safe_next_action":
        return ProjectBrainAnswer(
            intent=intent,
            text=_safe_next_answer(),
        )

    if intent == "memory_execution_distinction":
        return ProjectBrainAnswer(
            intent=intent,
            text=_memory_execution_answer(),
        )

    if intent == "app_py_risk":
        return ProjectBrainAnswer(
            intent=intent,
            text=_app_py_risk_answer(),
        )

    if intent == "practical_project_answer":
        return ProjectBrainAnswer(
            intent=intent,
            text=_practical_project_answer(),
        )

    return None

# NOVA_PROJECT_BRAIN_GENERAL_LIVE_SELECTOR_CLASSIFIER_20260702
# Keeps Project Brain general routing layered over the original classifier.
# The original classifier must be captured before this wrapper replaces it.

try:
    _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_CLASSIFIER_20260702 = (
        lambda user_text: False
    )

    def _nova_project_brain_live_selector_general_phrase_20260702(user_text):
        q = str(user_text or "").strip().lower()
        q = " ".join(
            q.replace("?", " ")
            .replace("!", " ")
            .split()
        )

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
        "what did we lock recently",
        "what got locked recently",
        "what is locked",
        "what's locked",
        "what got locked",
        "what did we lock",
        "next upgrade",
        ]

        return any(
            phrase in q
            for phrase in phrases
        )


    def should_handle_project_brain_general_question(user_text):
        q = str(user_text or "").strip().lower()
        q = " ".join(
            q.replace("?", " ")
            .replace("!", " ")
            .split()
        )

        if _nova_project_brain_live_selector_general_phrase_20260702(
            user_text
        ):
            return True

        return False

except Exception as _nova_project_brain_general_live_selector_classifier_error_20260702:
    print(
        "[NOVA_PROJECT_BRAIN_GENERAL_LIVE_SELECTOR_CLASSIFIER_20260702] failed:",
        _nova_project_brain_general_live_selector_classifier_error_20260702,
    )



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


def _legacy_build_project_brain_general_answer_497(user_text=""):
    print(
        "[DEBUG_PROJECT_BRAIN_GENERAL_CALLED]",
        user_text,
    )
    intent = classify_project_brain_intent(user_text)

    if intent == "mission_control":
        from nova_backend.services.project_brain_mission_control import (
            build_project_brain_mission_card,
        )

        card = build_project_brain_mission_card(
            user_text=str(user_text or ""),
        )

        return ProjectBrainAnswer(
            intent="mission_control",
            text=format_project_brain_mission_card(card),
        )

    q = _nova_project_brain_general_live_selector_normalize_20260702(user_text)
    if intent == "mission_control":
        return ProjectBrainAnswer(
            intent="mission_control",
            text=_mission_control_answer(user_text),
        )

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
        "next move",
        "current status",
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
        "current blocker",
        "actual blocker",
        "actual blocker on nova",
        "what is the actual blocker",
        "what is the actual blocker on nova",
        "what's the actual blocker",
        "what's the actual blocker on nova",
    ]

    if any(phrase in q for phrase in phrases):
        return True

    if q in {
        "status",
        "project status",
        "nova status",
        "current status",
        "current blocker",
        "actual blocker",
        "next",
        "next move",
        "what next",
        "what's next",
        "whats next",
        "what is next",
        "what should we do next",
    }:
        return True

    return False

def build_project_brain_general_answer(user_text=""):
    intent = classify_project_brain_intent(user_text)

    if intent == "locked_state":
        return ProjectBrainAnswer(
            intent="locked_state",
            text=_current_project_answer(user_text),
        )

    if intent == "actual_blocker":
        return ProjectBrainAnswer(
            intent="actual_blocker",
            text=(
                "Nova general intelligence blocker analysis:\n"
                "Current blocker: "
                "No active Project Brain intelligence blocker is open.\n"
                "Current checkpoint: "
                "Project Brain state is loaded from the freshness snapshot.\n"
                "Protected capabilities: "
                "Command Center, Project Brain Upgrade Radar, and "
                "Project Brain Operator Memory Writer are locked.\n"
                "Next move: "
                "continue focused validation through the Project Brain smoke stack.\n"
                "Fallback: "
                "If the blocker changes, return to the latest failing command, "
                "file path, error output, or smoke result and reclassify from "
                "the current project state."
            ),
        )


    if intent == "mission_control":
        from nova_backend.services.project_brain_mission_control import (
            build_project_brain_mission_card,
            format_project_brain_mission_card,
        )

        card = build_project_brain_mission_card(
            user_text=str(user_text or ""),
        )

        return ProjectBrainAnswer(
            intent="mission_control",
            text=format_project_brain_mission_card(card),
        )

    if intent == "current_project_state":
        q = _nova_project_brain_general_live_selector_normalize_20260702(
            user_text
        )

        broad_project_status = (
            "where are we at" in q
            or "where is nova at" in q
            or "nova status" in q
            or "project status" in q
        )

        if broad_project_status:
            return ProjectBrainAnswer(
                intent="project_brain_general_intelligence",
                text=(
                    "Source: Project Brain freshness snapshot.\n\n"
                    "Current Nova project state:\n"
                    "Current project: local Nova Flask app.\n\n"
                    "Project Brain is the general intelligence layer coordinating "
                    "memory, execution, routing, safety checks, and upgrades.\n\n"
                    "Current blocker: No active Project Brain intelligence blocker is open.\n\n"
                    "Next move: continue cleanup and validation through focused "
                    "smokes before expanding changes."
                ),
            )

        answer = _current_project_answer()

        return ProjectBrainAnswer(
            intent="current_project_state",
            text=str(answer),
        )

    if intent == "safe_next_action":
        return ProjectBrainAnswer(
            intent="safe_next_action",
            text=_safe_next_answer(),
        )

    if intent == "memory_execution_distinction":
        return ProjectBrainAnswer(
            intent="memory_execution_distinction",
            text=_memory_execution_answer(),
        )

    if intent == "app_py_risk":
        return ProjectBrainAnswer(
            intent="app_py_risk",
            text=_app_py_risk_answer(),
        )

    if intent == "practical_project_answer":
        return ProjectBrainAnswer(
            intent="practical_project_answer",
            text=_practical_project_answer(),
        )


    if (
    _nova_project_brain_command_center_question_20260702(user_text)
    and not (
        "where are we at with nova" in _nova_project_brain_general_live_selector_normalize_20260702(user_text)
        or "where are we at" in _nova_project_brain_general_live_selector_normalize_20260702(user_text)
        or "where is nova at" in _nova_project_brain_general_live_selector_normalize_20260702(user_text)
    )
):

        from nova_backend.services.project_brain_command_center import (
            build_project_brain_command_center_answer,
        )

        return ProjectBrainAnswer(
            intent="project_brain_general_status",
            text=(
                "Nova general intelligence project status:\n"
                "Working on the local Nova Flask app with Joe.\n"
                "Project Brain general intelligence layer is active.\n"
                "Next move: continue answer-quality alignment and Project Brain cleanup."
            ),
        )


    if should_handle_project_brain_general_question(user_text):
        from nova_backend.services.project_brain_live_answer_selector import (
            build_project_brain_live_answer,
        )

        live_answer = build_project_brain_live_answer(
            user_text=user_text,
        )

        if live_answer:
            live_text = str(
                getattr(
                    live_answer,
                    "text",
                    "",
                )
                or ""
            ).strip()

            if live_text:
                return ProjectBrainAnswer(
                    intent=str(
                        getattr(
                            live_answer,
                            "intent",
                            "",
                        )
                        or "project_brain_general"
                    ),
                    text=live_text,
                )

    if callable(_NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_BUILD_20260702):
        return _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_BUILD_20260702(
            user_text
        )

    return None

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

        return any(
            needle in text
            for needle in needles
        )

_NOVA_DECISION_LOG_PREVIOUS__CURRENT_PROJECT_ANSWER_20260701 = _current_project_answer


def _current_project_answer(*args, **kwargs):
    user_text = _nova_decision_log_user_text_20260701(
        *args,
        **kwargs
    )

    print(
        "[NOVA CURRENT PROJECT ANSWER CALLED]",
        user_text,
    )

    if _nova_is_decision_log_question_20260701(user_text):
        result = {
            "intent": "decision_log",
            "answer": _nova_decision_log_answer_20260701(limit=8),
            "route": "project_brain_general_intelligence",
            "risk": "low",
            "confidence": 0.91,
        }

        _nova_observe_project_brain_behavior_20260701(
            user_text,
            result["answer"],
        )

        return result

    return _NOVA_DECISION_LOG_PREVIOUS__CURRENT_PROJECT_ANSWER_20260701(
        *args,
        **kwargs
    )


print("[NOVA_PROJECT_BRAIN_DECISION_LOG_GENERAL_WIRE_20260701] installed on _current_project_answer")
# NOVA_PROJECT_BRAIN_COMMAND_CENTER_ROUTE_GATE_20260702
# Keeps Command Center prompts on the Project Brain general-intelligence route.
# Service-level gate only. No app.py route guard.
# NOVA_PROJECT_BRAIN_COMMAND_CENTER_ROUTE_GATE_20260702

_NOVA_PRE_COMMAND_CENTER_ROUTE_GATE_SHOULD_HANDLE_20260702 = (
    _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_CLASSIFIER_20260702
)


def should_handle_project_brain_general_question(user_text):
    try:
        if _nova_project_brain_command_center_question_20260702(user_text):
            return True
    except Exception:
        pass

    return _NOVA_PRE_COMMAND_CENTER_ROUTE_GATE_SHOULD_HANDLE_20260702(
        user_text
    )
