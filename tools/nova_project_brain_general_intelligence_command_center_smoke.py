from nova_backend.services.project_brain_general_intelligence import (
    build_project_brain_general_answer,
    should_handle_project_brain_general_question,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def answer_text(question):
    answer = build_project_brain_general_answer(question)
    assert_true(f"{question} returns answer object", hasattr(answer, "text"), answer)
    return answer.intent, answer.text


def main():
    print("NOVA PROJECT BRAIN GENERAL INTELLIGENCE COMMAND CENTER SMOKE")
    print("============================================================")

    assert_true("route gate handles command center", should_handle_project_brain_general_question("command center"))
    assert_true("route gate handles smoke question", should_handle_project_brain_general_question("what smoke should we run"))
    assert_true("route gate handles next upgrade", should_handle_project_brain_general_question("next upgrade"))
    assert_true("route gate handles recent changes", should_handle_project_brain_general_question("what changed recently"))
    assert_true("route gate preserves direct recall bypass", not should_handle_project_brain_general_question("what are we working on now"))

    intent, text = answer_text("command center")
    assert_true("command center intent", intent == "command_center", intent)
    assert_true("command center title", "Project Brain Command Center:" in text, text)
    assert_true("command center exact command", "Exact Next Command:" in text, text)

    intent, text = answer_text("what smoke should we run")
    assert_true("smoke question intent", intent == "command_center", intent)
    assert_true("smoke question command intent", "Command intent: smoke_selection" in text, text)
    assert_true("smoke question focused smokes", "Focused Smokes:" in text, text)

    intent, text = answer_text("next upgrade")
    assert_true("next upgrade intent", intent == "command_center", intent)
    assert_true("next upgrade command intent", "Command intent: next_move" in text, text)
    assert_true("next upgrade best move", "Best Move:" in text, text)

    intent, text = answer_text("what changed recently")
    assert_true("recent changes intent", intent == "command_center", intent)
    assert_true("recent changes command intent", "Command intent: recent_changes" in text, text)
    assert_true("recent changes log", "Recent Decision Log:" in text, text)

    direct = build_project_brain_general_answer("what are we working on now")
    assert_true("direct recall still bypasses general intelligence", direct is None, direct)

    print("")
    print("NOVA PROJECT BRAIN GENERAL INTELLIGENCE COMMAND CENTER SMOKE PASSED")


if __name__ == "__main__":
    main()

