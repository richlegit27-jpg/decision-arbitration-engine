from nova_backend.services.project_brain_general_intelligence import (
    build_project_brain_general_answer,
    classify_project_brain_intent,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def check(question):
    intent = classify_project_brain_intent(question)
    answer = build_project_brain_general_answer(question)

    assert_true(f"{question} classified", intent == "mission_control", intent)
    assert_true(f"{question} has answer", answer is not None, answer)
    assert_true(f"{question} answer intent", answer.intent == "mission_control", answer)
    text = answer.text
    lower = text.lower()

    assert_true(f"{question} title", "project brain mission control" in lower, text)
    assert_true(f"{question} current state", "current state:" in lower, text)
    assert_true(f"{question} intent field", "intent:" in lower, text)
    assert_true(f"{question} mission control intent", "intent: mission_control" in lower, text)
    assert_true(f"{question} risk field", "risk:" in lower, text)
    assert_true(f"{question} focused smoke", "focused smoke:" in lower, text)
    assert_true(f"{question} avoid rules", "avoid:" in lower, text)
    assert_true(f"{question} commit rule", "commit rule:" in lower, text)


def main():
    print("NOVA PROJECT BRAIN MISSION CONTROL GENERAL SMOKE")
    print("================================================")

    check("give me mission control")
    check("show me the mission card")
    check("operator mode")

    print("")
    print("NOVA PROJECT BRAIN MISSION CONTROL GENERAL SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
