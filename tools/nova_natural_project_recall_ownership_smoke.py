import json
import requests


BASE = "http://127.0.0.1:5001"


def ask(text):
    r = requests.post(
        f"{BASE}/api/chat",
        json={
            "message": text,
            "session_id": "natural_project_recall_ownership_smoke",
        },
        timeout=30,
    )

    assert r.status_code == 200, r.text

    return r.json()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_case(question):
    data = ask(question)

    route = (
        data.get("route")
        or data.get("route_taken")
        or data.get("debug", {}).get("route")
    )

    answer = (
        data.get("content")
        or data.get("message")
        or data.get("response")
        or data.get("assistant_message", {}).get("content")
        or ""
    )

    print()
    print("QUESTION:", question)
    print("ROUTE:", route)
    print("ANSWER:", answer[:200])

    require(
        route == "project_brain_general_intelligence",
        f"wrong route: {route}",
    )

    require(
        len(answer.strip()) > 20,
        "weak answer",
    )


print("NOVA NATURAL PROJECT RECALL OWNERSHIP SMOKE")
print("=" * 50)

check_case("where are we at with Nova right now?")
check_case("what is locked?")
check_case("what is left?")

print()
print("NOVA NATURAL PROJECT RECALL OWNERSHIP SMOKE PASSED")