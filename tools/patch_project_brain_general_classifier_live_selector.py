from pathlib import Path

path = Path("nova_backend/services/project_brain_general_intelligence.py")
text = path.read_text(encoding="utf-8")
marker = "# NOVA_PROJECT_BRAIN_GENERAL_LIVE_SELECTOR_EXPORTED_CLASSIFIER_20260702"

patch = r'''

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


def build_project_brain_general_answer(user_text=""):
    q = _nova_project_brain_general_live_selector_normalize_20260702(user_text)

    if q in {
        "what are we working on",
        "what are we working on now",
        "what are we working on right now",
    }:
        return None

    if should_handle_project_brain_general_question(user_text):
        from nova_backend.services.project_brain_live_answer_selector import (
            build_project_brain_live_answer,
        )

        return build_project_brain_live_answer(user_text=user_text).text

    if callable(_NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_BUILD_20260702):
        return _NOVA_PRE_LIVE_SELECTOR_PROJECT_BRAIN_GENERAL_BUILD_20260702(user_text)

    return None
'''

if marker not in text:
    path.write_text(text.rstrip() + "\n\n" + patch.lstrip(), encoding="utf-8")
    print(f"{path}: installed exported classifier + live selector build wrapper")
else:
    print(f"{path}: already installed")

smoke_path = Path("tools/nova_project_brain_general_classifier_live_selector_smoke.py")
smoke_code = r'''
from nova_backend.services.project_brain_general_intelligence import (
    build_project_brain_general_answer,
    should_handle_project_brain_general_question,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN GENERAL CLASSIFIER LIVE SELECTOR SMOKE")
    print("=========================================================")

    positive = [
        "where are we at with Nova right now?",
        "where are we at?",
        "where is Nova at?",
        "give me the Nova status without hype",
        "what should we do next?",
        "what's next?",
        "next concrete move",
        "should we patch app.py or test first?",
        "what does this failure mean?",
        "why did this fail?",
        "stale memory is hijacking the answer",
    ]

    for question in positive:
        result = should_handle_project_brain_general_question(question)
        answer = build_project_brain_general_answer(question)
        print(f"QUESTION: {question}")
        print(f"RESULT: {result}")
        print(f"ANSWER: {str(answer or '')[:500]}")
        assert_true(f"classifies {question}", result)
        assert_true(f"build returns answer {question}", bool(str(answer or '').strip()))

    next_answer = build_project_brain_general_answer("what should we do next?")
    assert_true(
        "next move uses decision context",
        "intent: next_move_judgment" in str(next_answer or "").lower(),
        next_answer,
    )

    exact_direct = [
        "what are we working on",
        "what are we working on now",
        "what are we working on right now",
    ]

    for question in exact_direct:
        result = should_handle_project_brain_general_question(question)
        answer = build_project_brain_general_answer(question)
        print(f"QUESTION: {question}")
        print(f"RESULT: {result}")
        print(f"ANSWER: {answer}")
        assert_true(f"keeps direct recall excluded {question}", not result)
        assert_true(f"direct recall build yields none {question}", answer is None)

    print("")
    print("NOVA PROJECT BRAIN GENERAL CLASSIFIER LIVE SELECTOR SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
'''

smoke_path.write_text(smoke_code.lstrip(), encoding="utf-8")
print(f"{smoke_path}: wrote")
