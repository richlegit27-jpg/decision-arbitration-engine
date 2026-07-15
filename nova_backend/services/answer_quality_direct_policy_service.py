from __future__ import annotations


def clean_answer_quality_text(value):
    return " ".join(
        str(value or "")
        .lower()
        .strip()
        .split()
    )


def get_direct_policy_answer(user_text: str):
    clean = clean_answer_quality_text(user_text)

    answers = {
        "what is the difference between memory and execution in nova": (
            "Memory is what Nova knows and retains: project facts, Richard's preferences, "
            "current checkpoint, and durable decisions. "
            "Execution is what Nova does right now: run commands, patch files, call /api/chat, "
            "test behavior, or return an output. "
            "Simple split: memory = what Nova knows; execution = what Nova does. "
            "Memory should guide answers, but execution is the live action path."
        ),

        "why should we not patch blindly right now": (
            "Do not patch blindly because app.py has many guard layers and a blind edit "
            "can hide the real failure. "
            "Read the failure first, identify the exact route/file, make one small change, "
            "then run py_compile and the relevant smoke test. "
            "Blind patching creates noisy diffs; smoke-backed patches keep the project stable."
        ),
    }

    return answers.get(clean)