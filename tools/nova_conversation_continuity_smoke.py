import json
import time
from urllib import request as urllib_request


API_URL = "http://127.0.0.1:5001/api/chat"


def post_chat(message, session_id):
    payload = {
        "message": message,
        "session_id": session_id,
        "attachments": [],
    }

    data = json.dumps(payload).encode("utf-8")

    last_error = None

    for attempt in range(1, 4):
        try:
            req = urllib_request.Request(
                API_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib_request.urlopen(req, timeout=20) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")

            assert status == 200
            return json.loads(body)

        except Exception as exc:
            last_error = exc
            time.sleep(0.8 * attempt)

    raise AssertionError(
        f"chat request failed after retries: {last_error}"
    )


def extract_answer(data):
    assistant = data.get("assistant_message") or {}
    return (
        data.get("text")
        or data.get("content")
        or assistant.get("text")
        or assistant.get("content")
        or ""
    )


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA CONVERSATION CONTINUITY SMOKE")
    print("=================================")

    session_id = f"continuity_{int(time.time())}"

    post_chat(
        "We are working on Nova Project Brain cleanup and consolidation.",
        session_id,
    )

    data = post_chat(
        "what were we talking about",
        session_id,
    )

    answer = extract_answer(data)

    print("ANSWER:", answer)

    lower = answer.lower()

    assert_true(
        "recalls Nova",
        "nova" in lower,
    )

    assert_true(
        "recalls Project Brain",
        "project brain" in lower,
    )

    assert_true(
        "avoids empty context failure",
        "do not have enough recent session context" not in lower,
    )

    print("")
    print("NOVA CONVERSATION CONTINUITY SMOKE PASSED")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print("")
        print("NOVA CONVERSATION CONTINUITY SMOKE FAILED")
        print(exc)
        raise SystemExit(1)