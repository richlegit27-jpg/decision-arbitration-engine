from __future__ import annotations

import time
import requests


BASE_URL = "http://127.0.0.1:5001"
CHAT_URL = BASE_URL + "/api/chat"


def require(condition, label, detail=""):
    if not condition:
        raise AssertionError(label + (" DETAIL: " + repr(detail) if detail else ""))

    print("PASS", label)


def ask(session_id, message):
    print()
    print("=" * 90)
    print("USER:", message)
    print("=" * 90)

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

    print("STATUS:", response.status_code)

    require(response.status_code == 200, "/api/chat status 200", response.text[:1000])

    payload = response.json()

    text = (
        payload.get("text")
        or payload.get("content")
        or (
            payload.get("assistant_message", {}).get("text")
            if isinstance(payload.get("assistant_message"), dict)
            else ""
        )
        or (
            payload.get("assistant_message", {}).get("content")
            if isinstance(payload.get("assistant_message"), dict)
            else ""
        )
        or ""
    ).strip()

    print()
    print("NOVA:")
    print(text)

    require(bool(text), "Nova returned non-empty answer")

    return text.lower()


def main():
    print("NOVA PHASE 7B LIVE UNRESOLVED THREAD BEHAVIOR SMOKE")
    print("=" * 90)

    health = requests.get(BASE_URL + "/api/health", timeout=20)

    print("HEALTH:", health.status_code)

    require(health.status_code == 200, "Nova health reachable", health.text[:1000])

    session_id = "phase_7b_live_threads_" + str(int(time.time()))

    print("SESSION:", session_id)

    ask(
        session_id,
        "we are testing whether Nova can keep quiet unresolved threads",
    )

    defer_text = ask(
        session_id,
        "after this let's fix attachments",
    )

    require(
        "attachment" in defer_text or "after this" in defer_text or "later" in defer_text,
        "Nova acknowledges deferred attachments naturally",
        defer_text,
    )

    current_text = ask(
        session_id,
        "why did the conversation state brain matter",
    )

    require(
        "conversation" in current_text or "state" in current_text or "brain" in current_text,
        "current explicit topic receives relevant answer",
        current_text,
    )

    require(
        "attachment" not in current_text[:500],
        "deferred attachments do not hijack unrelated current answer",
        current_text,
    )

    recall_text = ask(
        session_id,
        "what was the other thing we still needed to do",
    )

    require(
        "attachment" in recall_text,
        "explicit unresolved-thread recall returns deferred attachments",
        recall_text,
    )

    done_text = ask(
        session_id,
        "we're done with attachments",
    )

    require(
        "done" in done_text or "good" in done_text or "okay" in done_text or "attachment" in done_text,
        "Nova accepts explicit thread completion",
        done_text,
    )

    open_text = ask(
        session_id,
        "what's still open",
    )

    open_excerpt = open_text[:700]

    attachment_is_absent = (
        "attachment" not in open_excerpt
    )

    attachment_is_explicitly_closed = (
        "attachment" in open_excerpt
        and any(
            closure_word in open_excerpt
            for closure_word in (
                "closed",
                "done",
                "resolved",
                "complete",
                "finished",
                "no longer open",
                "not open",
            )
        )
    )

    require(
        (
            attachment_is_absent
            or attachment_is_explicitly_closed
        ),
        "completed attachments thread is no longer reported open",
        open_text,
    )

    print()
    print("=" * 90)
    print("NOVA PHASE 7B LIVE UNRESOLVED THREAD BEHAVIOR: REAL PASS")
    print("=" * 90)


if __name__ == "__main__":
    main()
