import json
import os
import sys
import time
from dataclasses import dataclass
from typing import List, Sequence

import requests


BASE_URL = os.environ.get("NOVA_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT = float(os.environ.get("NOVA_SMOKE_TIMEOUT", "20"))


WEAK_SIGNALS = [
    "i don't have enough context",
    "i do not have enough context",
    "i'm not sure what project",
    "i am not sure what project",
    "can you provide more details",
    "could you provide more details",
    "as an ai language model",
    "i can't access your local",
    "i cannot access your local",
    "i don't have access to your files",
    "i do not have access to your files",
]


@dataclass
class Case:
    name: str
    question: str
    expected_groups: Sequence[Sequence[str]]
    min_groups: int
    avoid: Sequence[str]


def _lower_text(value):
    return str(value or "").lower()


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


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def api_status():
    for path in ("/api/health", "/api/state", "/api/sessions"):
        try:
            response = _request_with_retry("GET", BASE_URL + path)
            if response.status_code < 500:
                print("PASS api status")
                return
        except Exception:
            pass

    raise AssertionError("api status FAILED")


def ask(question, session_id):
    payload = {
        "message": question,
        "session_id": session_id,
        "attachments": [],
    }

    response = _request_with_retry(
        "POST",
        BASE_URL + "/api/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
    )

    assert_true("api status", response.status_code == 200, f"status={response.status_code}")

    try:
        data = response.json()
    except Exception as exc:
        raise AssertionError(f"json response FAILED {exc}") from exc

    answer = _extract_answer(data)

    assert_true("answer exists", bool(answer.strip()), f"data keys={list(data.keys())}")

    return answer, data


def matched_groups(answer, expected_groups):
    text = _lower_text(answer)
    hits = []

    for group in expected_groups:
        if any(_lower_text(term) in text for term in group):
            hits.append(group)

    return hits


def run_case(case, index):
    session_id = f"general_intelligence_{int(time.time())}_{index}"

    answer, data = ask(case.question, session_id)

    print("")
    print(f"CASE: {case.name}")
    print(f"QUESTION: {case.question}")
    print(f"ANSWER: {answer[:700]}")

    hits = matched_groups(answer, case.expected_groups)
    missing = [group for group in case.expected_groups if group not in hits]
    bad = [term for term in case.avoid if _lower_text(term) in _lower_text(answer)]

    assert_true(
        f"{case.name} concept coverage",
        len(hits) >= case.min_groups,
        f"hits={len(hits)} min={case.min_groups} missing={missing}",
    )

    assert_true(
        f"{case.name} avoids weak fallback",
        not bad,
        f"bad={bad}",
    )

    debug = data.get("debug", {}) if isinstance(data, dict) else {}
    route = ""
    if isinstance(debug, dict):
        route = str(debug.get("route_taken") or debug.get("route") or "")

    if route:
        print(f"ROUTE: {route}")

    return True


def main():
    print("NOVA GENERAL INTELLIGENCE SMOKE")
    print("================================")

    api_status()

    cases = [
        Case(
            name="project paraphrase recall",
            question="where are we at with Nova right now?",
            expected_groups=[
                ["nova"],
                ["flask", "local nova", "local app"],
                ["answer quality", "answer-policy", "quality smoke"],
                ["project state", "current project state", "current checkpoint", "checkpoint"],
                ["next move", "blocker", "what's next", "what should we do next"],
            ],
            min_groups=4,
            avoid=WEAK_SIGNALS,
        ),
        Case(
            name="safe next action judgment",
            question="before we change more code, what is the safest next move?",
            expected_groups=[
                ["git status", "working tree", "dirty"],
                ["py_compile", "compile"],
                ["smoke", "test"],
                ["checkpoint", "commit"],
                ["smallest", "targeted"],
            ],
            min_groups=3,
            avoid=WEAK_SIGNALS + [
                "just start coding",
                "dive into implementation",
            ],
        ),
        Case(
            name="memory execution distinction",
            question="separate what Nova remembers from what Nova is actively doing",
            expected_groups=[
                ["memory"],
                ["remembers", "knows", "retains", "stored", "durable"],
                ["execution"],
                ["does", "runs", "actions", "commands", "patch", "live"],
            ],
            min_groups=4,
            avoid=WEAK_SIGNALS,
        ),
        Case(
            name="architecture risk judgment",
            question="what is risky about app.py right now?",
            expected_groups=[
                ["app.py"],
                ["large", "too many", "stack", "guard", "hooks", "route"],
                ["after_request", "before_request", "app.run", "late hooks"],
                ["audit", "smoke"],
                ["regression", "protect", "cleanup"],
            ],
            min_groups=3,
            avoid=WEAK_SIGNALS,
        ),
        Case(
            name="practical project answer",
            question="give me the project answer in practical terms, not a pep talk",
            expected_groups=[
                ["nova"],
                ["current", "right now", "checkpoint"],
                ["answer quality", "project state", "memory recall"],
                ["next", "blocker", "safe move"],
                ["test", "smoke", "git status"],
            ],
            min_groups=4,
            avoid=WEAK_SIGNALS + [
                "you've got this",
                "keep going",
                "great job",
            ],
        ),
    ]

    passed = 0

    failures = []

    for index, case in enumerate(cases, start=1):
        try:
            run_case(case, index)
            passed += 1
        except Exception as exc:
            failures.append((case.name, str(exc)))
            print(f"FAIL {case.name}: {exc}")

    total = len(cases)

    print("")
    print(f"NOVA GENERAL INTELLIGENCE SCORE: {passed}/{total}")

    if failures:
        print("")
        print("FAILED CASES")
        print("============")
        for name, detail in failures:
            print(f"- {name}: {detail}")

    assert_true("general intelligence minimum", passed >= 4, f"passed={passed} total={total}")

    print("")
    print("NOVA GENERAL INTELLIGENCE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
