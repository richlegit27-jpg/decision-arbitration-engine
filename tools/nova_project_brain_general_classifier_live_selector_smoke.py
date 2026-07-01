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
