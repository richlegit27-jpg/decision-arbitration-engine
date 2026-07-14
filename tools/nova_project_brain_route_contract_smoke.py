import json
import os
import time
from dataclasses import dataclass
from typing import Sequence

import requests


BASE_URL = os.environ.get("NOVA_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT = float(os.environ.get("NOVA_SMOKE_TIMEOUT", "20"))


@dataclass(frozen=True)
class RouteCase:
    name: str
    question: str
    expected_route: str
    expected_terms: Sequence[str]


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
    if not isinstance(data, dict):
        return ""

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
    if not isinstance(data, dict):
        return ""

    debug = data.get("debug")
    if isinstance(debug, dict):
        return str(debug.get("route_taken") or debug.get("route") or "")

    return ""


def ask(question, index):
    payload = {
        "message": question,
        "session_id": f"project_brain_route_contract_{int(time.time())}_{index}",
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
    assert_true("route exists", bool(route), f"debug={data.get('debug')}")

    return answer, route


def run_case(case, index):
    answer, route = ask(case.question, index)
    lower_answer = answer.lower()

    print("")
    print(f"CASE: {case.name}")
    print(f"QUESTION: {case.question}")
    print(f"ROUTE: {route}")
    print(f"ANSWER: {answer[:650]}")

    assert_true(
        f"{case.name} route",
        route == case.expected_route,
        f"expected={case.expected_route} actual={route}",
    )

    missing = [term for term in case.expected_terms if term.lower() not in lower_answer]

    assert_true(
        f"{case.name} answer terms",
        not missing,
        f"missing={missing}",
    )


def main():
    print("NOVA PROJECT BRAIN ROUTE CONTRACT SMOKE")
    print("=======================================")

    cases = [
        RouteCase(
            name="exact project state keeps direct recall",
            question="what are we working on now",
            expected_route="project_state_current_memory_direct_recall",
expected_terms=[
    "Nova",
    "project state",
    "Current checkpoint",
],
        ),
        RouteCase(
            name="project paraphrase uses general intelligence",
            question="where are we at with Nova right now?",
            expected_route="project_brain_general_intelligence",
            expected_terms=[
                "local Nova Flask app",
                "general intelligence",
                "Next move",
            ],
        ),
        RouteCase(
            name="safe coding judgment uses general intelligence",
            question="before we change more code, what is the safest next move?",
            expected_route="project_brain_general_intelligence",
            expected_terms=[
                "git status",
                "py_compile",
                "smoke",
            ],
        ),
        RouteCase(
            name="memory execution concept uses general intelligence",
            question="separate what Nova remembers from what Nova is actively doing",
            expected_route="project_brain_general_intelligence",
            expected_terms=[
                "Memory",
                "Execution",
                "what Nova knows",
                "what Nova does",
            ],
        ),
    ]

    for index, case in enumerate(cases, start=1):
        run_case(case, index)

    print("")
    print("NOVA PROJECT BRAIN ROUTE CONTRACT SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
