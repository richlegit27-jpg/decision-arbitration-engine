import json
import time
from urllib import request as urllib_request


API_URL = "http://127.0.0.1:5001/api/chat"

QUESTIONS = [
    "what are we working on now",
    "where are we at with Nova right now?",
    "what's the next concrete move on the project?",
    "give me the Nova status without hype",
]

BAD_TERMS = [
        "and fres Current blocker",
    "and fres Current blocker",
    "text: Current Nova project state",
    "Next concrete move / safe move: Next concrete move / safe move",
    "Current safe direction: Next concrete move",
    "live_answer_sample.py",
    "idle/generic fallback",
    "finish Nova project brain answer quality",
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def post_chat(question):
    payload = {
        "message": question,
        "session_id": f"project_answer_readability_{int(time.time())}",
        "attachments": [],
    }

    req = urllib_request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=20) as response:
        body = response.read().decode("utf-8", errors="replace")
        data = json.loads(body)

    assistant = data.get("assistant_message") or {}
    answer = (
        data.get("text")
        or data.get("content")
        or assistant.get("text")
        or assistant.get("content")
        or ""
    )
    route = (
        (data.get("debug") or {}).get("route_taken")
        or (data.get("debug") or {}).get("route")
        or (assistant.get("meta") or {}).get("route")
        or ""
    )

    return answer, route


def main():
    print("NOVA PROJECT ANSWER READABILITY SMOKE")
    print("=====================================")

    for question in QUESTIONS:
        print("")
        print("QUESTION:", question)
        answer, route = post_chat(question)
        print("ROUTE:", route)
        print("ANSWER:", answer[:900])

        lower = answer.lower()
        bad = [term for term in BAD_TERMS if term.lower() in lower]

        assert_true("answer exists", bool(answer.strip()))
        assert_true("Project Brain present", "project brain" in lower)
        assert_true("no malformed fragments", not bad, f"bad={bad}")

    print("")
    print("NOVA PROJECT ANSWER READABILITY SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
