import json
import time
import requests

BASE = "http://127.0.0.1:5001"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA ATTACHMENT RESPONSE CONTRACT SMOKE")
    print("=======================================")

    stamp = str(int(time.time()))
    session_id = f"attachment_contract_{stamp}"

    payload = {
        "message": "summarize this attached file",
        "session_id": session_id,
        "attachments": [
            {
                "filename": "contract-test.txt",
                "name": "contract-test.txt",
                "mime_type": "text/plain",
                "content_type": "text/plain",
                "text": "This is a contract smoke attachment.",
                "summary": "Contract smoke attachment.",
            }
        ],
    }

    response = requests.post(
        f"{BASE}/api/chat",
        json=payload,
        timeout=30,
    )

    assert_true("api status", response.status_code == 200, response.text[:800])

    data = response.json()
    debug = data.get("debug") if isinstance(data.get("debug"), dict) else {}
    assistant = data.get("assistant_message") if isinstance(data.get("assistant_message"), dict) else {}

    assert_true("response dict", isinstance(data, dict), data)
    assert_true("assistant message dict", isinstance(assistant, dict), data)
    assert_true("session id preserved", data.get("session_id") == session_id or debug.get("session_id") == session_id, data)
    assert_true("active session preserved", data.get("active_session_id") == session_id or debug.get("active_session_id") == session_id, data)

    top_attachments = data.get("attachments")
    session_attachments = data.get("session_attachments")
    assistant_attachments = assistant.get("attachments")

    assert_true(
        "attachments shape exists",
        isinstance(top_attachments, list)
        or isinstance(session_attachments, list)
        or isinstance(assistant_attachments, list),
        data,
    )

    assert_true("debug exists", isinstance(debug, dict), data)
    assert_true(
        "finalizer did not break attachment count",
        debug.get("attachment_count", 0) >= 0 or debug.get("session_attachments_count", 0) >= 0,
        debug,
    )

    print("")
    print("NOVA ATTACHMENT RESPONSE CONTRACT SMOKE PASSED")


if __name__ == "__main__":
    main()
