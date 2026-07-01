import json
import os
import time
from urllib import request, error


BASE_URL = os.environ.get("NOVA_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT = float(os.environ.get("NOVA_SMOKE_TIMEOUT", "20"))


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def _extract_answer(data):
    assistant_message = data.get("assistant_message")
    if isinstance(assistant_message, dict):
        for key in ("text", "content"):
            value = assistant_message.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for key in ("text", "content", "answer", "response"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _extract_route(data):
    debug = data.get("debug")
    if isinstance(debug, dict):
        return str(debug.get("route_taken") or debug.get("route") or "")

    return str(data.get("route_taken") or data.get("route") or "")


def ask(message):
    payload = {
        "message": message,
        "session_id": f"mission_control_api_smoke_{int(time.time())}",
        "attachments": [],
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        BASE_URL + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            return data, _extract_answer(data), _extract_route(data)
    except error.URLError as exc:
        raise RuntimeError(f"Request failed for {message!r}: {exc}") from exc


def check_mission_control(question):
    print("")
    print(f"QUESTION: {question}")

    data, answer, route = ask(question)
    lower = answer.lower()

    print(f"ROUTE: {route}")
    print(f"ANSWER: {answer[:1200]}")

    assert_true(f"{question} route", route == "project_brain_general_intelligence", route)
    assert_true(f"{question} title", "project brain mission control" in lower, answer)
    assert_true(f"{question} current state", "current state:" in lower, answer)
    assert_true(f"{question} intent", "intent:" in lower, answer)
    assert_true(f"{question} mission control intent", "intent: mission_control" in lower, answer)
    assert_true(f"{question} risk", "risk:" in lower, answer)
    assert_true(f"{question} focused smoke", "focused smoke:" in lower, answer)
    assert_true(f"{question} avoid", "avoid:" in lower, answer)
    assert_true(f"{question} commit rule", "commit rule:" in lower, answer)
    assert_true(f"{question} decision engine", "decision engine v1" in lower, answer)


def check_direct_recall_still_separate():
    print("")
    print("QUESTION: what are we working on now")

    data, answer, route = ask("what are we working on now")
    lower = answer.lower()

    print(f"ROUTE: {route}")
    print(f"ANSWER: {answer[:900]}")

    assert_true("direct recall route preserved", route == "project_state_current_memory_direct_recall", route)
    assert_true("direct recall not mission card title", not lower.startswith("project brain mission control:"), answer)
    assert_true("direct recall has no mission fields", "focused smoke:" not in lower and "commit rule:" not in lower, answer)
    assert_true("direct recall has project state", "current nova project state" in lower, answer)


def main():
    print("NOVA PROJECT BRAIN MISSION CONTROL API SMOKE")
    print("============================================")

    check_mission_control("give me mission control")
    check_mission_control("show me the mission card")
    check_mission_control("operator mode")

    check_direct_recall_still_separate()

    print("")
    print("NOVA PROJECT BRAIN MISSION CONTROL API SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
