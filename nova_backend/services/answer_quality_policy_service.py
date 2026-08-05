from __future__ import annotations


def _clean_question(value):
    return " ".join(
        str(value or "").lower().strip().split()
    )


_ANSWER_QUALITY_POLICY = {

    "what test should we run before touching code": (
        "Before touching code, run the smallest checks that prove the current behavior is safe:\n\n"
        "1. `python -m py_compile` on the Python files you may touch.\n"
        "2. The most relevant focused smoke test.\n"
        "3. `git status --short` before staging or committing.\n\n"
        "For Nova intelligence/memory work, use:\n\n"
        "python -m py_compile .\\app.py\n"
        "python .\\tools\\nova_answer_quality_smoke.py\n"
        "python .\\tools\\nova_project_state_memory_api_smoke.py\n"
        "python .\\tools\\nova_phase_4i_guard_stack_audit_smoke.py\n"
        "git status --short"
    ),

    "what is the difference between memory and execution in nova": (
        "Memory is what Nova knows and retains: project facts, Richard's preferences, "
        "current checkpoint, and durable decisions. "
        "Execution is what Nova does right now: run commands, patch files, "
        "call /api/chat, test behavior, or return an output. "
        "Simple split: memory = what Nova knows; execution = what Nova does. "
        "Memory should guide answers, but execution is the live action path."
    ),

    "why should we not patch blindly right now": (
        "Do not patch blindly because app.py has many guard layers and a blind edit can hide the real failure. "
        "Read the failure first, identify the exact route/file, make one small change, then run py_compile and the relevant smoke test. "
        "Blind patching creates noisy diffs; smoke-backed patches keep the project stable."
    ),
}


def get_answer_quality_policy_answer(user_text):
    clean = _clean_question(user_text)

    direct = _ANSWER_QUALITY_POLICY.get(clean)

    if direct:
        return direct

    if any(
        trigger in clean
        for trigger in (
            "what test should we run before touching code",
            "what tests should we run before touching code",
            "what should we run before touching code",
            "what test before touching code",
            "what tests before touching code",
            "before touching code",
            "before patching",
            "before we patch",
        )
    ):
        return _ANSWER_QUALITY_POLICY[
            "what test should we run before touching code"
        ]

    return None