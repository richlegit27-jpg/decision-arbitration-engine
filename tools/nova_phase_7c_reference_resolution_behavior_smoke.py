import os
import time

import requests


BASE_URL = os.environ.get(
    "NOVA_BASE_URL",
    "http://127.0.0.1:5001",
).rstrip("/")


def require(condition, label, detail=""):
    if not condition:
        raise AssertionError(
            label
            + (
                " DETAIL: "
                + repr(detail)
                if detail
                else ""
            )
        )

    print("PASS", label)


def chat(session_id, message):
    print()
    print("=" * 90)
    print("USER:", message)
    print("=" * 90)

    response = requests.post(
        BASE_URL + "/api/chat",
        json={
            "session_id": session_id,
            "message": message,
        },
        timeout=120,
    )

    print("STATUS:", response.status_code)

    require(
        response.status_code == 200,
        "/api/chat status 200",
        response.text[:1000],
    )

    data = response.json()

    assistant = (
        data.get("assistant_message")
        if isinstance(
            data.get("assistant_message"),
            dict,
        )
        else {}
    )

    answer = str(
        data.get("text")
        or data.get("content")
        or assistant.get("text")
        or assistant.get("content")
        or ""
    ).strip()

    print()
    print("NOVA:")
    print(answer)

    require(
        bool(answer),
        "Nova returned non-empty answer",
    )

    return answer.lower()


def main():
    print(
        "NOVA PHASE 7C LIVE REFERENCE RESOLUTION BEHAVIOR SMOKE"
    )
    print("=" * 90)

    health = requests.get(
        BASE_URL + "/api/health",
        timeout=30,
    )

    print("HEALTH:", health.status_code)

    require(
        health.status_code == 200,
        "Nova health reachable",
    )

    session_id = (
        "phase_7c_live_reference_"
        + str(int(time.time()))
    )

    print("SESSION:", session_id)

    chat(
        session_id,
        (
            "We are comparing two possible upgrades. "
            "The first option is improving voice controls. "
            "The second option is adding session search. "
            "Do not choose yet; just keep both options straight."
        ),
    )

    second = chat(
        session_id,
        "Which was the second one?",
    )

    require(
        "session" in second
        and "search" in second,
        "ordinal reference resolves the second option",
        second,
    )

    switched = chat(
        session_id,
        (
            "Separate question for a moment: "
            "why does whitespace matter in mobile layouts?"
        ),
    )

    require(
        any(
            marker in switched
            for marker in (
                "space",
                "spacing",
                "whitespace",
                "layout",
            )
        ),
        "explicit topic switch receives relevant answer",
        switched,
    )

    resumed = chat(
        session_id,
        (
            "Go back to the second option from before "
            "I changed the subject. What was it?"
        ),
    )

    require(
        "session" in resumed
        and "search" in resumed,
        "cross-topic reference restores the correct option",
        resumed,
    )

    corrected = chat(
        session_id,
        "Not the second one?the first one.",
    )

    require(
        "voice" in corrected,
        "latest ordinal correction selects the first option",
        corrected,
    )

    ordinary = chat(
        session_id,
        "Separate question: what is two plus two?",
    )

    require(
        "4" in ordinary
        or "four" in ordinary,
        "ordinary question receives ordinary answer",
        ordinary,
    )

    require(
        "voice control" not in ordinary
        and "session search" not in ordinary,
        "older option thread does not hijack ordinary question",
        ordinary,
    )

    print()
    print("=" * 90)
    print(
        "NOVA PHASE 7C LIVE REFERENCE RESOLUTION BEHAVIOR: REAL PASS"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
