import time
import requests


BASE_URL = "http://127.0.0.1:5001/api/chat"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def ask(question):
    session_id = f"decision_log_api_{int(time.time())}_{abs(hash(question)) % 10000}"
    response = requests.post(
        BASE_URL,
        json={
            "message": question,
            "session_id": session_id,
            "attachments": [],
        },
        timeout=30,
    )

    assert_true(f"{question} api status", response.status_code == 200, response.text[:500])

    data = response.json()
    assistant = data.get("assistant_message") or {}
    answer = (
        assistant.get("text")
        or assistant.get("content")
        or data.get("text")
        or data.get("answer")
        or ""
    )

    debug = data.get("debug") or {}
    route = (
        debug.get("route_taken")
        or debug.get("route")
        or data.get("route_taken")
        or data.get("route")
        or ""
    )

    print("")
    print(f"QUESTION: {question}")
    print(f"ROUTE: {route}")
    print(f"ANSWER: {answer[:1200]}")

    return route, answer


def main():
    print("NOVA PROJECT BRAIN DECISION LOG API SMOKE")
    print("=========================================")

    for question in (
        "what changed recently",
        "show me the recent decisions",
        "what did we lock recently",
    ):
        route, answer = ask(question)
        blob = (route + "\n" + answer).lower()

        assert_true(f"{question} route", "project_brain_general_intelligence" in blob, blob)
        assert_true(f"{question} decision log title", "recent decision log" in blob, answer)
        assert_true(f"{question} recent changes title", "what changed recently" in blob, answer)
        assert_true(f"{question} operator timeline", "operator timeline" in blob, answer)
        assert_true(f"{question} direct recall protected", "direct project-state recall remains" in blob, answer)

    route, answer = ask("what are we working on now")
    blob = (route + "\n" + answer).lower()

    assert_true("direct recall route preserved", "project_state_current_memory_direct_recall" in blob, blob)
    assert_true("direct recall not decision log", "recent decision log" not in blob, answer)
    assert_true("direct recall has project state", "current nova project state" in blob, answer)

    print("")
    print("NOVA PROJECT BRAIN DECISION LOG API SMOKE PASSED")


if __name__ == "__main__":
    main()
