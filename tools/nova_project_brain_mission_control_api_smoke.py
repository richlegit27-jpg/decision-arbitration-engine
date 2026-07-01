import time
import requests


BASE_URL = "http://127.0.0.1:5001/api/chat"


MISSION_CASES = [
    "give me mission control",
    "show me the mission card",
    "operator mode",
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
    route = (
        debug.get("route_taken")
        or debug.get("route")
        or data.get("route")
        or ""
    )

    print("")
    print(f"QUESTION: {question}")
    print(f"ROUTE: {route}")
    print(f"ANSWER: {answer[:1400]}")

    return data, route, answer


def assert_mission_control_answer(question, route, answer):
    assert_true(f"{question} route", route == "project_brain_general_intelligence", route)
    assert_true(f"{question} title", "Project Brain Mission Control:" in answer, answer)
    assert_true(f"{question} current state", "Current state:" in answer, answer)
    assert_true(f"{question} intent", "Intent:" in answer, answer)
    assert_true(f"{question} mission control intent", "mission_control" in answer, answer)
    assert_true(f"{question} risk", "Risk:" in answer, answer)
    assert_true(f"{question} focused smoke", "Focused smoke:" in answer, answer)
    assert_true(f"{question} avoid", "Avoid:" in answer, answer)
    assert_true(f"{question} commit rule", "Commit rule:" in answer, answer)
    assert_true(f"{question} decision engine", "Decision Engine" in answer, answer)

    assert_true(f"{question} operator plan section", "Operator Plan:" in answer, answer)
    assert_true(f"{question} operator recommended move", "Operator recommended move:" in answer, answer)
    assert_true(f"{question} operator why", "Operator why:" in answer, answer)
    assert_true(f"{question} operator work type", "Operator work type:" in answer, answer)
    assert_true(f"{question} operator risk", "Operator risk:" in answer, answer)
    assert_true(f"{question} operator focused smokes", "Operator focused smokes:" in answer, answer)
    assert_true(f"{question} operator avoid rules", "Operator avoid rules:" in answer, answer)
    assert_true(f"{question} operator stop rule", "Operator stop rule:" in answer, answer)


def main():
    print("NOVA PROJECT BRAIN MISSION CONTROL API SMOKE")
    print("============================================")

    stamp = str(int(time.time()))

    for index, question in enumerate(MISSION_CASES, start=1):
        _, route, answer = post_chat(
            question,
            session_id=f"mission_control_operator_plan_api_{stamp}_{index}",
        )
        assert_mission_control_answer(question, route, answer)

    _, route, answer = post_chat(
        "what are we working on now",
        session_id=f"mission_control_direct_recall_guard_{stamp}",
    )

    assert_true("direct recall route preserved", route == "project_state_current_memory_direct_recall", route)
    assert_true("direct recall not mission card title", "Project Brain Mission Control:" not in answer, answer)
    assert_true("direct recall has no mission fields", "Operator Plan:" not in answer, answer)
    assert_true("direct recall has project state", "Current Nova project state:" in answer, answer)

    print("")
    print("NOVA PROJECT BRAIN MISSION CONTROL API SMOKE PASSED")


if __name__ == "__main__":
    main()
