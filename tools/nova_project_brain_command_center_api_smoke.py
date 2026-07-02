import time
import requests


BASE_URL = "http://127.0.0.1:5001/api/chat"


CASES = [
    ("command center", "command_center", "Project Brain Command Center:"),
    ("what smoke should we run", "command_center", "Command intent: smoke_selection"),
    ("next upgrade", "command_center", "Command intent: next_move"),
    ("what changed recently", "command_center", "Command intent: recent_changes"),
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def post_chat(question, session_id):
    response = requests.post(
        BASE_URL,
        json={
            "message": question,
            "session_id": session_id,
            "attachments": [],
        },
        timeout=20,
    )
    assert_true(f"{question} api status", response.status_code == 200, response.text)

    data = response.json()
    assistant = data.get("assistant_message") or {}

    answer = (
        assistant.get("text")
        or assistant.get("content")
        or data.get("text")
        or data.get("content")
        or ""
    )

    debug = data.get("debug") or {}
    route = debug.get("route_taken") or debug.get("route") or data.get("route") or ""

    print("")
    print(f"QUESTION: {question}")
    print(f"ROUTE: {route}")
    print(f"ANSWER: {answer[:1400]}")

    return route, answer


def main():
    print("NOVA PROJECT BRAIN COMMAND CENTER API SMOKE")
    print("===========================================")

    stamp = str(int(time.time()))

    for index, (question, expected_route, expected_text) in enumerate(CASES, start=1):
        route, answer = post_chat(
            question,
            session_id=f"command_center_api_{stamp}_{index}",
        )

        assert_true(f"{question} route", route == "project_brain_general_intelligence", route)
        assert_true(f"{question} command center title", "Project Brain Command Center:" in answer, answer)
        assert_true(f"{question} expected text", expected_text in answer, answer)
        assert_true(f"{question} exact next command", "Exact Next Command:" in answer, answer)
        assert_true(f"{question} focused smokes", "Focused Smokes:" in answer, answer)
        assert_true(f"{question} loop guard", "Loop Guard:" in answer, answer)

    route, answer = post_chat(
        "what are we working on now",
        session_id=f"command_center_direct_recall_guard_{stamp}",
    )

    assert_true("direct recall route preserved", route == "project_state_current_memory_direct_recall", route)
    assert_true("direct recall not command center", "Project Brain Command Center:" not in answer, answer)
    assert_true("direct recall has project state", "Current Nova project state:" in answer, answer)

    print("")
    print("NOVA PROJECT BRAIN COMMAND CENTER API SMOKE PASSED")


if __name__ == "__main__":
    main()
