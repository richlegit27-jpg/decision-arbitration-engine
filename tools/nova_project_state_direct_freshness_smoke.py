import json
import os
import time

import requests


BASE_URL = os.environ.get("NOVA_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT = float(os.environ.get("NOVA_SMOKE_TIMEOUT", "20"))

STALE_TERMS = [
    "answer-policy intelligence is 100%",
    "real general intelligence still needs improvement",
    "moving direct policy behavior into cleaner prompt",
    "Make Nova answer quality smoke retry reload resets",
]

REQUIRED_TERMS = [
    "Project Brain",
    "freshness snapshot",
    "context builder",
    "answer freshness",
    "fallback",
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def request_chat(question):
    payload = {
        "message": question,
        "session_id": f"project_state_direct_freshness_{int(time.time())}",
        "attachments": [],
    }

    response = requests.post(
        BASE_URL + "/api/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=TIMEOUT,
    )

    assert_true("api status", response.status_code == 200, f"status={response.status_code}")
    data = response.json()

    debug = data.get("debug") if isinstance(data.get("debug"), dict) else {}
    route = str(debug.get("route_taken") or debug.get("route") or "")

    assistant_message = data.get("assistant_message")
    answer = ""

    if isinstance(assistant_message, dict):
        answer = str(assistant_message.get("text") or assistant_message.get("content") or "")

    if not answer:
        answer = str(data.get("text") or data.get("content") or data.get("answer") or "")

    return answer, route


def main():
    print("NOVA PROJECT STATE DIRECT FRESHNESS SMOKE")
    print("=========================================")

    answer, route = request_chat("what are we working on now")
    lower = answer.lower()

    print("")
    print("ROUTE:", route)
    print("ANSWER:", answer[:900])

    assert_true(
        "direct route preserved",
        route == "project_state_current_memory_direct_recall",
        route,
    )

    missing = [term for term in REQUIRED_TERMS if term.lower() not in lower]
    assert_true("fresh direct answer terms", not missing, f"missing={missing}")

    stale = [term for term in STALE_TERMS if term.lower() in lower]
    assert_true("stale direct answer terms removed", not stale, f"stale={stale}")

    print("")
    print("NOVA PROJECT STATE DIRECT FRESHNESS SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
