import json
import os
import time
from dataclasses import dataclass
from typing import Sequence

import requests


BASE_URL = os.environ.get("NOVA_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT = float(os.environ.get("NOVA_SMOKE_TIMEOUT", "20"))


@dataclass(frozen=True)
class Case:
    name: str
    question: str
    expected_route: str
    expected_terms: Sequence[str]
    avoid_terms: Sequence[str] = ()


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


def ask(question, index):
    payload = {
        "message": question,
        "session_id": f"project_brain_broadening_{int(time.time())}_{index}",
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
    lower = answer.lower()

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

    missing = [term for term in case.expected_terms if term.lower() not in lower]
    bad = [term for term in case.avoid_terms if term.lower() in lower]

    assert_true(f"{case.name} expected terms", not missing, f"missing={missing}")
    assert_true(f"{case.name} avoids bad terms", not bad, f"bad={bad}")


def main():
    print("NOVA PROJECT BRAIN CLASSIFIER BROADENING SMOKE")
    print("==============================================")

    cases = [
        Case(
            name="plain project status",
            question="where's the project at?",
            expected_route="project_brain_general_intelligence",
            expected_terms=["Nova", "current", "Next move"],
        ),
        Case(
            name="actual blocker",
            question="what's the actual blocker on Nova?",
            expected_route="project_brain_general_intelligence",
            expected_terms=["Nova", "general intelligence", "fallback"],
        ),
        Case(
            name="safe to code",
            question="are we safe to code yet or should we test first?",
            expected_route="project_brain_general_intelligence",
            expected_terms=["git status", "py_compile", "smoke"],
        ),
        Case(
            name="app py dangerous",
            question="why is app.py dangerous right now?",
            expected_route="project_brain_general_intelligence",
            expected_terms=["app.py", "before_request", "after_request"],
        ),
        Case(
            name="memory or execution",
            question="is this a memory problem or an execution problem?",
            expected_route="project_brain_general_intelligence",
            expected_terms=["Memory", "Execution", "what Nova knows", "what Nova does"],
            avoid_terms=["Stored memory"],
        ),
        Case(
            name="know vs do",
            question="what should Nova know vs what should Nova do?",
            expected_route="project_brain_general_intelligence",
            expected_terms=["Memory", "Execution", "knows", "does"],
            avoid_terms=["Stored memory"],
        ),
        Case(
            name="no hype project answer",
            question="give me the Nova status without hype",
            expected_route="project_brain_general_intelligence",
            expected_terms=["Nova", "project-state", "safe"],
            avoid_terms=["you've got this", "great job"],
        ),
        Case(
            name="next concrete project move",
            question="what's the next concrete move on the project?",
            expected_route="project_brain_general_intelligence",
            expected_terms=["Nova", "safe move", "smoke"],
        ),
    ]

    for index, case in enumerate(cases, start=1):
        run_case(case, index)

    print("")
    print("NOVA PROJECT BRAIN CLASSIFIER BROADENING SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
