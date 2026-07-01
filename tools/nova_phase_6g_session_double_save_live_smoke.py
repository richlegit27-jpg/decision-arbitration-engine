import json
import time
import urllib.request


BASE = "http://127.0.0.1:5001"
CHAT_URL = BASE + "/api/chat"
SESSION_URL = BASE + "/api/sessions/{session_id}"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def post_chat(payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        CHAT_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def get_session(session_id):
    with urllib.request.urlopen(SESSION_URL.format(session_id=session_id), timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def count_user_text(messages, text):
    return sum(
        1
        for msg in messages
        if isinstance(msg, dict)
        and str(msg.get("role") or "").lower() == "user"
        and str(msg.get("text") or msg.get("content") or "") == text
    )


def main():
    print("NOVA PHASE 6G SESSION DOUBLE-SAVE LIVE SMOKE")
    print("")

    stamp = str(int(time.time()))
    session_id = f"phase6g_session_double_save_{stamp}"

    first = f"phase6g first message {stamp}"
    second = f"phase6g second message {stamp}"

    result1 = post_chat({
        "message": first,
        "session_id": session_id,
        "attachments": [],
    })

    assert_true("first chat ok", result1.get("ok") is True)

    result2 = post_chat({
        "message": second,
        "session_id": session_id,
        "attachments": [],
    })

    assert_true("second chat ok", result2.get("ok") is True)

    loaded = get_session(session_id)
    assert_true("session get ok", loaded.get("ok") is True)

    session = loaded.get("session") or {}
    messages = session.get("messages") or []

    print(f"Session id: {session_id}")
    print(f"Message count: {len(messages)}")
    print(f"First user count: {count_user_text(messages, first)}")
    print(f"Second user count: {count_user_text(messages, second)}")

    for index, msg in enumerate(messages, start=1):
        role = str(msg.get("role") or "")
        text = str(msg.get("text") or msg.get("content") or "")
        print(f"{index}. {role}: {text[:120]}")

    assert_true(
        "first user saved once",
        count_user_text(messages, first) == 1,
        f"messages={len(messages)}",
    )

    assert_true(
        "second user saved once",
        count_user_text(messages, second) == 1,
        f"messages={len(messages)}",
    )

    assert_true(
        "two-turn session has four messages",
        len(messages) == 4,
        f"messages={len(messages)}",
    )

    print("")
    print("NOVA PHASE 6G SESSION DOUBLE-SAVE LIVE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
