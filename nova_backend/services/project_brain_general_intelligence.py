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
    return (
        "Current Nova project state: Richard is working on the local Nova Flask app with Joe. "
        "The project-state memory recall fix is complete. The guard-stack audit smoke is installed. "
        "The Nova answer-quality smoke is installed. The larger answer-quality 95 smoke is passing, "
        "and the new general intelligence smoke exposed the real next blocker: nearby phrasing and "
        "judgment questions are still falling into old fallback, memory-write, or generic chat paths. "
        "Current checkpoint: move project-brain behavior into a reusable intent/policy layer instead "
        "of adding more brittle exact-prompt patches. Next move: protect project-brain answers for "
        "paraphrases, safe coding judgment, memory-vs-execution distinction, app.py architecture risk, "
        "and practical project-status answers. Safe validation: run py_compile, targeted smokes, "
        "then git status before committing."
    )


def _safe_next_answer() -> str:
    return (
        "Safest next move before changing more code: stop and verify the working tree first. "
        "Run `git status --short`, then `python -m py_compile` on the files being touched, "
        "then the smallest targeted smoke test for the behavior. For this Nova work, that means "
        "`python -m py_compile .\\app.py`, `python -m py_compile .\\tools\\nova_general_intelligence_smoke.py`, "
        "then `python .\\tools\\nova_general_intelligence_smoke.py`. If it passes, run the project-state, "
        "answer-quality, and guard-stack audit smokes. Keep the patch small and targeted; commit only "
        "after the smoke board is green."
    )


def _memory_execution_answer() -> str:
    return (
        "Memory is what Nova remembers, knows, retains, and uses as durable project context: "
        "Richard's preferences, the current Nova checkpoint, project-state facts, blockers, and decisions. "
        "Execution is what Nova is actively doing live: running commands, patching files, calling `/api/chat`, "
        "testing behavior, building a plan, or returning an output. Simple split: memory = what Nova knows; "
        "execution = what Nova does. Memory should guide execution, but it should not hijack a concept question "
        "and turn it into a memory-save response."
    )


def _app_py_risk_answer() -> str:
    return (
        "`app.py` risk right now: it is too large and has too many stacked guards, wrappers, routes, "
        "`before_request` hooks, and `after_request` hooks competing for priority. The guard-stack audit "
        "already protects the most dangerous structural issue: no late hooks below `app.run`. The remaining "
        "architecture risk is behavior priority: a lower-quality fallback, memory-write path, or generic chat "
        "route can answer before the project-brain layer gets a chance. Keep protecting this with regression "
        "smokes, then gradually move reusable intelligence into service files instead of growing `app.py`."
    )


def _practical_project_answer() -> str:
    return (
        "Practical Nova project answer: the core project-state recall path is green, answer-quality policy is "
        "green, and the new blocker is general intelligence routing. The current safe move is to make one small "
        "project-brain priority layer that catches nearby project and judgment questions before fallback routes. "
        "Then run `python -m py_compile .\\app.py`, `python -m py_compile .\\tools\\nova_general_intelligence_smoke.py`, "
        "`python .\\tools\\nova_general_intelligence_smoke.py`, the answer-quality smoke, the project-state memory "
        "API smoke, and the guard-stack audit smoke. After that, check `git status --short` and commit the clean patch."
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
