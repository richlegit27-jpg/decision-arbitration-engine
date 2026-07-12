import time

import requests


URL = "http://127.0.0.1:5001/api/chat"

CANDIDATES = (
    "improve voice controls",
    "add session search",
    "tighten billing alerts",
)

WEB_FALLBACK = "no verified fresh web results were retrieved"


def post(session_id, message):
    response = requests.post(
        URL,
        json={
            "session_id": session_id,
            "message": message,
        },
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    assistant = (
        data.get("assistant_message")
        if isinstance(data.get("assistant_message"), dict)
        else {}
    )

    debug = (
        data.get("debug")
        if isinstance(data.get("debug"), dict)
        else {}
    )

    answer = str(
        data.get("text")
        or data.get("content")
        or assistant.get("text")
        or assistant.get("content")
        or ""
    ).strip()

    route = str(
        data.get("route_taken")
        or data.get("route")
        or debug.get("route_taken")
        or debug.get("route")
        or ""
    ).strip().lower()

    return answer, route


def require(condition, message, evidence=""):
    if not condition:
        raise AssertionError(
            message
            + (
                "\nEVIDENCE: "
                + repr(evidence)
                if evidence
                else ""
            )
        )

    print("PASS", message)


stamp = str(int(time.time()))

cases = (
    (
        "WITHOUT LAUNCH",
        "During this conversation, use three candidates "
        "in this exact order. First: improve voice controls. "
        "Second: add session search. Third: tighten billing alerts.",
        "Which candidate should we work on next, and why?",
    ),
    (
        "WITH LAUNCH",
        "During this conversation, use three launch candidates "
        "in this exact order. First: improve voice controls. "
        "Second: add session search. Third: tighten billing alerts.",
        "Which launch candidate should we choose, and why?",
    ),
)


print("=" * 100)
print("PHASE 7C STATEFUL CANDIDATE RECALL REGRESSION")
print("=" * 100)


for index, (label, setup, followup) in enumerate(
    cases,
    start=1,
):
    session_id = (
        f"phase_7c_regression_{stamp}_{index}"
    )

    print()
    print("-" * 100)
    print(label)
    print("-" * 100)

    setup_answer, setup_route = post(
        session_id,
        setup,
    )

    require(
        setup_route == "chat",
        f"{label} setup stays on chat route",
        setup_route,
    )

    require(
        WEB_FALLBACK not in setup_answer.lower(),
        f"{label} setup avoids false web fallback",
        setup_answer,
    )

    require(
        all(
            candidate in setup_answer.lower()
            for candidate in CANDIDATES
        ),
        f"{label} setup preserves all candidates",
        setup_answer,
    )

    answer, route = post(
        session_id,
        followup,
    )

    require(
        route == "chat",
        f"{label} follow-up stays on chat route",
        route,
    )

    require(
        WEB_FALLBACK not in answer.lower(),
        f"{label} follow-up avoids false web fallback",
        answer,
    )

    require(
        CANDIDATES[0] in answer.lower(),
        f"{label} recalls and selects first candidate",
        answer,
    )

    print("ANSWER:", repr(answer[:500]))


print()
print("=" * 100)
print("PHASE 7C STATEFUL CANDIDATE RECALL: REAL PASS")
print("FALSE WEB ROUTING: BLOCKED")
print("ORDERED CROSS-TURN RECALL: LOCKED")
print("=" * 100)
