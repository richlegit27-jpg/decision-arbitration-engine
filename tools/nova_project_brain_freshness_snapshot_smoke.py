import json
import os
import time

import requests

from nova_backend.services.project_brain_context_builder import build_practical_project_answer
from nova_backend.services.project_brain_freshness_snapshot import (
    SNAPSHOT_VERSION,
    build_project_brain_freshness_snapshot,
)


BASE_URL = os.environ.get("NOVA_BASE_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT = float(os.environ.get("NOVA_SMOKE_TIMEOUT", "20"))


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


def ask(question):
    payload = {
        "message": question,
        "session_id": f"project_brain_freshness_snapshot_{int(time.time())}",
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
    return _extract_answer(data), _extract_route(data)


def main():
    print("NOVA PROJECT BRAIN FRESHNESS SNAPSHOT SMOKE")
    print("===========================================")

    snapshot = build_project_brain_freshness_snapshot()

    assert_true("snapshot version", snapshot.version == SNAPSHOT_VERSION, snapshot.version)
    assert_true("checkpoint exists", bool(snapshot.checkpoint), snapshot)
    assert_true("checkpoint locked", "decision engine v1" in snapshot.checkpoint.lower(), snapshot.checkpoint)
    assert_true("routing locked", "project brain routing" in snapshot.checkpoint.lower(), snapshot.checkpoint)
    assert_true("mission control locked", "mission control v1.1" in snapshot.checkpoint.lower(), snapshot.checkpoint)
    assert_true("operator prompts locked", "operator prompts" in snapshot.checkpoint.lower(), snapshot.checkpoint)
    assert_true("blocker closed", "no active decision engine blocker" in snapshot.blocker.lower(), snapshot.blocker)
    assert_true("mission blocker closed", "mission control blocker" in snapshot.blocker.lower(), snapshot.blocker)
    assert_true("failure interpreter blocker closed", "failure interpreter blocker" in snapshot.blocker.lower(), snapshot.blocker)
    assert_true("cleanup risk noted", "cleanup/consolidation" in snapshot.blocker.lower(), snapshot.blocker)
    assert_true("next move cleanup", "project brain cleanup/consolidation" in snapshot.next_move.lower(), snapshot.next_move)
    assert_true("next move preserves Mission Control", "mission control v1.1" in snapshot.next_move.lower(), snapshot.next_move)
    assert_true("no new app guard", "without adding another app.py guard" in snapshot.next_move.lower(), snapshot.next_move)
    assert_true("validation includes py_compile", any("py_compile" in command for command in snapshot.validation), snapshot.validation)
    assert_true("validation includes git status", any("git status --short" in command for command in snapshot.validation), snapshot.validation)
    assert_true("available smokes found", len(snapshot.available_smoke_files) >= 5, snapshot.available_smoke_files)

    direct_answer = build_practical_project_answer()
    direct_lower = direct_answer.lower()

    assert_true("direct answer has Decision Engine", "decision engine v1" in direct_lower, direct_answer)
    assert_true("direct answer has Mission Control", "mission control v1.1" in direct_lower, direct_answer)
    assert_true("direct answer has Project Brain", "project brain" in direct_lower, direct_answer)
    assert_true("direct answer has cleanup", "cleanup/consolidation" in direct_lower, direct_answer)
    assert_true("direct answer has no new guard", "without adding another app.py guard" in direct_lower, direct_answer)

    api_answer, route = ask("give me the Nova status without hype")
    api_lower = api_answer.lower()

    assert_true("api route", route == "project_brain_general_intelligence", route)
    assert_true("api answer has Decision Engine", "decision engine v1" in api_lower, api_answer)
    assert_true("api answer has Mission Control", "mission control v1.1" in api_lower, api_answer)
    assert_true("api answer has Project Brain", "project brain" in api_lower, api_answer)
    assert_true("api answer has routing locked", "project brain routing" in api_lower, api_answer)
    assert_true("api answer has cleanup", "cleanup/consolidation" in api_lower, api_answer)
    assert_true("api answer has no new guard", "without adding another app.py guard" in api_lower, api_answer)

    print("")
    print("NOVA PROJECT BRAIN FRESHNESS SNAPSHOT SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
