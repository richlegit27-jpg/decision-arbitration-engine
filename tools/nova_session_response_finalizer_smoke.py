
from nova_backend.services.session_response_finalizer import (
    clean_session_id,
    extract_active_session_id,
    extract_session_id,
    finalize_session_response_payload,
    normalize_session_response_payload,
    should_normalize_session_response,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA SESSION RESPONSE FINALIZER SMOKE")
    print("=====================================")

    assert_true("clean session id", clean_session_id(" abc ") == "abc")

    payload = {
        "assistant_message": {
            "text": "hello",
        },
        "debug": {
            "requested_session_id": "session_123",
        },
    }

    assert_true("extract session id", extract_session_id(payload) == "session_123")
    assert_true("should normalize", should_normalize_session_response(payload) is True)

    normalized = normalize_session_response_payload(payload)

    assert_true("top session id added", normalized["session_id"] == "session_123", normalized)
    assert_true("top active session id added", normalized["active_session_id"] == "session_123", normalized)
    assert_true("debug session id added", normalized["debug"]["session_id"] == "session_123", normalized)
    assert_true("debug active session id added", normalized["debug"]["active_session_id"] == "session_123", normalized)
    assert_true("assistant session id added", normalized["assistant_message"]["session_id"] == "session_123", normalized)
    assert_true("marker added", normalized["debug"]["session_response_finalizer"] is True, normalized)

    existing = {
        "session_id": "old_session",
        "active_session_id": "old_active",
        "debug": {
            "requested_session_id": "new_session",
        },
    }

    preserved = normalize_session_response_payload(existing, preserve_existing=True)
    assert_true("preserve top session", preserved["session_id"] == "old_session", preserved)
    assert_true("preserve top active", preserved["active_session_id"] == "old_active", preserved)

    overwritten = normalize_session_response_payload(existing, session_id="new_session", active_session_id="new_session", preserve_existing=False)
    assert_true("overwrite top session", overwritten["session_id"] == "new_session", overwritten)
    assert_true("overwrite top active", overwritten["active_session_id"] == "new_session", overwritten)

    session_payload = {
        "session": {
            "id": "session_from_object",
            "title": "Test",
        },
        "text": "hello",
    }

    finalized = finalize_session_response_payload(session_payload)
    assert_true("finalized session object id", finalized["session_id"] == "session_from_object", finalized)
    assert_true("active from session object", extract_active_session_id(finalized) == "session_from_object", finalized)

    normal_chat = {
        "text": "hello only",
    }

    untouched = finalize_session_response_payload(normal_chat)
    assert_true("normal payload untouched", untouched == normal_chat, untouched)

    print("")
    print("NOVA SESSION RESPONSE FINALIZER SMOKE PASSED")


if __name__ == "__main__":
    main()
