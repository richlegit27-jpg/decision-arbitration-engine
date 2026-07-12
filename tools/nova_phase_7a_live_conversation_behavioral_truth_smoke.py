from __future__ import annotations

import json
import time
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:5001"

CHAT_URL = (
    BASE_URL
    +
    "/api/chat"
)

SESSION_URL = (
    BASE_URL
    +
    "/api/sessions/{session_id}"
)


FORBIDDEN_COMMAND_CENTER_MARKERS = (
    "project brain command center",
    "operator contract",
    "routing diagnostics",
    "smoke list",
)


IDLE_FALLBACK_MARKERS = (
    "i'm here. what would you like to work on",
    "how can i help",
    "what would you like to work on",
)


def heading(
    title: str,
) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def require(
    condition: bool,
    label: str,
    detail: Any = "",
) -> None:
    if not condition:
        raise AssertionError(
            (
                label
                +
                (
                    " DETAIL: "
                    + repr(
                        detail
                    )
                    if detail != ""
                    else ""
                )
            )
        )

    print(
        "PASS",
        label,
    )


def extract_text(
    payload: Any,
) -> str:
    if not isinstance(
        payload,
        dict,
    ):
        return ""

    assistant = (
        payload.get(
            "assistant_message"
        )
        if isinstance(
            payload.get(
                "assistant_message"
            ),
            dict,
        )
        else {}
    )

    values = (
        payload.get(
            "text"
        ),
        payload.get(
            "content"
        ),
        payload.get(
            "reply"
        ),
        assistant.get(
            "text"
        ),
        assistant.get(
            "content"
        ),
        assistant.get(
            "message"
        ),
    )

    for value in values:
        text = str(
            value
            or ""
        ).strip()

        if text:
            return text

    return ""


def collect_route_hints(
    value: Any,
) -> list[str]:
    hints: list[str] = []

    if isinstance(
        value,
        dict,
    ):
        for key, child in value.items():
            key_probe = str(
                key
            ).strip().lower()

            if key_probe in {
                "route",
                "route_taken",
                "strategy",
                "intent",
                "mode",
                "source",
            }:
                if isinstance(
                    child,
                    (
                        str,
                        int,
                        float,
                        bool,
                    ),
                ):
                    hints.append(
                        str(
                            child
                        )
                    )

            hints.extend(
                collect_route_hints(
                    child
                )
            )

    elif isinstance(
        value,
        list,
    ):
        for child in value:
            hints.extend(
                collect_route_hints(
                    child
                )
            )

    return hints


def flatten_strings(
    value: Any,
) -> list[str]:
    values: list[str] = []

    if isinstance(
        value,
        str,
    ):
        values.append(
            value
        )

    elif isinstance(
        value,
        dict,
    ):
        for child in value.values():
            values.extend(
                flatten_strings(
                    child
                )
            )

    elif isinstance(
        value,
        list,
    ):
        for child in value:
            values.extend(
                flatten_strings(
                    child
                )
            )

    return values


def contains_marker(
    text: str,
    markers: tuple[str, ...],
) -> bool:
    probe = str(
        text
        or ""
    ).lower()

    return any(
        marker in probe
        for marker in markers
    )


def uses_project_brain_route(
    payload: dict[str, Any],
) -> bool:
    route_hints = [
        str(
            value
        ).lower()
        for value in collect_route_hints(
            payload
        )
    ]

    return any(
        "project_brain_general_intelligence"
        in value
        for value in route_hints
    )


def ask(
    session_id: str,
    message: str,
) -> tuple[
    dict[str, Any],
    str,
]:
    heading(
        "USER: "
        +
        message
    )

    response = requests.post(
        CHAT_URL,
        json={
            "session_id": session_id,
            "client_session_id": session_id,
            "active_session_id": session_id,
            "message": message,
            "user_text": message,
            "attachments": [],
        },
        timeout=180,
    )

    print(
        "STATUS:",
        response.status_code,
    )

    require(
        response.status_code == 200,
        "live /api/chat status 200",
        response.text[
            :2000
        ],
    )

    try:
        payload = response.json()

    except Exception as exc:
        raise AssertionError(
            (
                "live /api/chat returned non-JSON "
                +
                repr(
                    response.text[
                        :2000
                    ]
                )
            )
        ) from exc

    text = extract_text(
        payload
    )

    print(
        "PAYLOAD KEYS:",
        sorted(
            payload.keys()
        ),
    )

    print(
        "ROUTE HINTS:",
        collect_route_hints(
            payload
        ),
    )

    print()

    print(
        "NOVA:"
    )

    print(
        text
    )

    require(
        bool(
            text
        ),
        "live Nova answer is non-empty",
        payload,
    )

    return (
        payload,
        text,
    )


def main() -> None:
    heading(
        "SERVER HEALTH"
    )

    try:
        health_response = requests.get(
            BASE_URL
            +
            "/api/health",
            timeout=20,
        )

    except Exception as exc:
        raise AssertionError(
            (
                "Nova is not reachable at "
                +
                BASE_URL
                +
                ". Start the normal Nova Flask server first."
            )
        ) from exc

    print(
        "HEALTH STATUS:",
        health_response.status_code,
    )

    require(
        health_response.status_code == 200,
        "live Nova health endpoint reachable",
        health_response.text[
            :1000
        ],
    )

    session_id = (
        "phase_7a_live_behavior_"
        +
        str(
            int(
                time.time()
            )
        )
    )

    heading(
        "FRESH SESSION"
    )

    print(
        "SESSION ID:",
        session_id,
    )

    baseline_payload, baseline_text = ask(
        session_id,
        (
            "what should we do next with Nova "
            "right now"
        ),
    )

    baseline_exercised_project_brain = (
        uses_project_brain_route(
            baseline_payload
        )
        or contains_marker(
            baseline_text,
            (
                "project brain command center",
                "best move:",
                "operator contract",
            ),
        )
    )

    require(
        baseline_exercised_project_brain,
        "baseline exercises Project Brain priority behavior",
        {
            "text": baseline_text,
            "route_hints": collect_route_hints(
                baseline_payload
            ),
        },
    )

    correction = (
        "don't give me project command center shit "
        "just tell me normally"
    )

    correction_payload, correction_text = ask(
        session_id,
        correction,
    )

    require(
        not contains_marker(
            correction_text,
            IDLE_FALLBACK_MARKERS,
        ),
        "correction turn does not collapse to idle fallback",
        correction_text,
    )

    heading(
        "LIVE SESSION PERSISTENCE TRUTH"
    )

    session_response = requests.get(
        SESSION_URL.format(
            session_id=session_id
        ),
        timeout=30,
    )

    print(
        "SESSION STATUS:",
        session_response.status_code,
    )

    require(
        session_response.status_code == 200,
        "live session can be read",
        session_response.text[
            :2000
        ],
    )

    session_payload = session_response.json()

    session_corpus = "\n".join(
        flatten_strings(
            session_payload
        )
    ).lower()

    require(
        correction
        in session_corpus,
        "latest conversational correction persisted in live session",
    )

    follow_payload, follow_text = ask(
        session_id,
        (
            "so basically are we done with "
            "the self improvement stuff now"
        ),
    )

    require(
        not uses_project_brain_route(
            follow_payload
        ),
        "Project Brain priority route stands down after correction",
        collect_route_hints(
            follow_payload
        ),
    )

    require(
        not contains_marker(
            follow_text,
            FORBIDDEN_COMMAND_CENTER_MARKERS,
        ),
        "next live answer obeys Command Center rejection",
        follow_text,
    )

    require(
        not contains_marker(
            follow_text,
            IDLE_FALLBACK_MARKERS,
        ),
        "next live answer is not idle generic fallback",
        follow_text,
    )

    require(
        len(
            follow_text.split()
        )
        >=
        4,
        "next live answer contains a real conversational response",
        follow_text,
    )

    nested_payload, nested_text = ask(
        session_id,
        "why did that matter",
    )

    require(
        not uses_project_brain_route(
            nested_payload
        ),
        "nested follow-up remains out of Project Brain priority route",
        collect_route_hints(
            nested_payload
        ),
    )

    require(
        not contains_marker(
            nested_text,
            FORBIDDEN_COMMAND_CENTER_MARKERS,
        ),
        "nested follow-up preserves conversational correction",
        nested_text,
    )

    require(
        not contains_marker(
            nested_text,
            IDLE_FALLBACK_MARKERS,
        ),
        "nested follow-up does not lose conversation",
        nested_text,
    )

    require(
        len(
            nested_text.split()
        )
        >=
        4,
        "nested follow-up receives a substantive answer",
        nested_text,
    )

    heading(
        "PHASE 7A LIVE BEHAVIORAL VERDICT"
    )

    print(
        "BASELINE PROJECT BRAIN: EXERCISED"
    )

    print(
        "CORRECTION: PERSISTED"
    )

    print(
        "NEXT MESSAGE: NORMAL CONVERSATION"
    )

    print(
        "PROJECT BRAIN BYPASS: LIVE"
    )

    print(
        "NESTED FOLLOW-UP: LIVE"
    )

    print()

    print(
        "=" * 100
    )

    print(
        "NOVA PHASE 7A LIVE CONVERSATION BEHAVIORAL TRUTH: REAL PASS"
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":
    main()
