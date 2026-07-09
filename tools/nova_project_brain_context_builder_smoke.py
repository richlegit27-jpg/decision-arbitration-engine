import json
import os
import time

import requests


BASE_URL = os.environ.get("NOVA_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT = float(os.environ.get("NOVA_SMOKE_TIMEOUT", "20"))


STALE_TERMS = [
    "new blocker is general intelligence routing",
    "make one small project-brain priority layer",
    "clean patch",
    "catches nearby project and judgment questions before fallback routes",
]


REQUIRED_TERMS = [
    "Project Brain",
    "context builder",
    "Current blocker",
    "answer freshness",
    "Next concrete move",
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def _request_with_retry(method, url, **kwargs):
    last_error = None

    for attempt in range(1, 8):
        try:
            response = requests.request(method, url, timeout=TIMEOUT, **kwargs)

            if response.status_code in (502, 503, 504):
                last_error = RuntimeError(f"HTTP {response.status_code}")
                time.sleep(0.35 * attempt)
                continue

            return response

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ReadTimeout,
        ) as exc:
            last_error = exc
            time.sleep(0.35 * attempt)

    raise RuntimeError(f"request failed after retries: {last_error}")


def _extract_answer(data):
    assistant_message = data.get("assistant_message")
    if isinstance(assistant_message, dict):
        for key in ("text", "content", "message", "answer"):
            value = assistant_message.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for key in ("text", "content", "message", "answer", "response"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _extract_route(data):
    debug = data.get("debug")
    if isinstance(debug, dict):
        return str(debug.get("route_taken") or debug.get("route") or "")
    return ""


def ask(question):
    payload = {
        "message": question,
        "session_id": f"project_brain_context_builder_{int(time.time())}",
        "attachments": [],
    }

    response = _request_with_retry(
        "POST",
        BASE_URL + "/api/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
    )

    assert_true("api status", response.status_code == 200, f"status={response.status_code}")

    data = response.json()
    answer = _extract_answer(data)
    route = _extract_route(data)

    assert_true("answer exists", bool(answer), f"keys={list(data.keys())}")
    assert_true("route", route == "project_brain_general_intelligence", route)

    return answer


def main():
    print("NOVA PROJECT BRAIN CONTEXT BUILDER SMOKE")
    print("========================================")

    answer = ask("give me the Nova status without hype")
    lower = answer.lower()

    print("")
    print("ANSWER:")
    print(answer[:900])

    missing = [term for term in REQUIRED_TERMS if term.lower() not in lower]
    stale = [term for term in STALE_TERMS if term.lower() in lower]

    assert_true("required context terms", not missing, f"missing={missing}")
    assert_true("stale hardcoded terms removed", not stale, f"stale={stale}")

    print("")
    print("NOVA PROJECT BRAIN CONTEXT BUILDER SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
