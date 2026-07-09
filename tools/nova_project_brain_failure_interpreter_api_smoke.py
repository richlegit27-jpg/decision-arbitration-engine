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
        "session_id": f"failure_interpreter_api_smoke_{int(time.time())}",
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


def check_failure(question, expected_type, expected_terms):
    print("")
    print(f"QUESTION: {question.splitlines()[0]}")

    data, answer, route = ask(question)
    lower = answer.lower()

    print(f"ROUTE: {route}")
    print(f"ANSWER: {answer[:1400]}")

    assert_true("route", route == "project_brain_general_intelligence", route)
    assert_true("mission control title", "project brain mission control" in lower, answer)
    assert_true("mission control intent", "intent: mission_control" in lower, answer)
    assert_true("failure type field", "failure type:" in lower, answer)
    assert_true("failure severity field", "failure severity:" in lower, answer)
    assert_true("failure patch target field", "failure patch target:" in lower, answer)
    assert_true("failure next command field", "failure next command:" in lower, answer)
    assert_true("expected failure type", f"failure type: {expected_type}" in lower, answer)

    for term in expected_terms:
        assert_true(
            f"includes {term}",
            term.lower() in lower,
            answer,
        )


def check_direct_recall_not_hijacked():
    print("")
    print("QUESTION: what are we working on now")

    data, answer, route = ask("what are we working on now")
    lower = answer.lower()

    print(f"ROUTE: {route}")
    print(f"ANSWER: {answer[:900]}")

    assert_true("direct recall route", route == "project_state_current_memory_direct_recall", route)
    assert_true("not mission card", not lower.startswith("project brain mission control:"), answer)
    assert_true("no failure fields", "failure type:" not in lower and "failure next command:" not in lower, answer)


def main():
    print("NOVA PROJECT BRAIN FAILURE INTERPRETER API SMOKE")
    print("================================================")

    check_failure(
        question=(
            "give me mission control\n\n"
            "NOVA ANSWER QUALITY SMOKE FAILED missing expected signals"
        ),
        expected_type="smoke_contract_mismatch",
        expected_terms=[
            "smoke_contract_mismatch",
            "source wording",
            "smoke contract",
            "nova_answer_quality_smoke.py",
        ],
    )

    check_failure(
        question=(
            "operator mode\n\n"
            "NOVA REGRESSION SMOKE FAILED: Request failed for 'what should we work on next': "
            "<urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>"
        ),
        expected_type="server_not_running",
        expected_terms=[
            "server_not_running",
            "python app.py",
            "runtime",
        ],
    )

    check_failure(
        question=(
            "show me the mission card\n\n"
            "Sorry: IndentationError: unexpected indent (nova_project_brain_freshness_snapshot_smoke.py, line 106)"
        ),
        expected_type="python_compile_error",
        expected_terms=[
            "python_compile_error",
            "py_compile",
            "nova_project_brain_freshness_snapshot_smoke.py",
        ],
    )

    check_direct_recall_not_hijacked()

    print("")
    print("NOVA PROJECT BRAIN FAILURE INTERPRETER API SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
