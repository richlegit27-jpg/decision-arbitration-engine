from pathlib import Path

SERVICE = Path("nova_backend/services/session_response_finalizer.py")
SMOKE = Path("tools/nova_session_response_finalizer_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
from __future__ import annotations

from copy import deepcopy
from typing import Any


SESSION_RESPONSE_FINALIZER_NAME = "nova_session_response_finalizer_v1"


def clean_session_id(value: Any) -> str:
    return str(value or "").strip()


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _first_clean(*values: Any) -> str:
    for value in values:
        cleaned = clean_session_id(value)
        if cleaned:
            return cleaned
    return ""


def extract_session_id(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""

    debug = _dict(payload.get("debug"))
    assistant_message = _dict(payload.get("assistant_message"))
    session = _dict(payload.get("session"))

    return _first_clean(
        payload.get("session_id"),
        payload.get("active_session_id"),
        payload.get("requested_session_id"),
        debug.get("session_id"),
        debug.get("active_session_id"),
        debug.get("requested_session_id"),
        session.get("id"),
        assistant_message.get("session_id"),
    )


def extract_active_session_id(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""

    debug = _dict(payload.get("debug"))
    session = _dict(payload.get("session"))

    return _first_clean(
        payload.get("active_session_id"),
        debug.get("active_session_id"),
        payload.get("session_id"),
        debug.get("session_id"),
        session.get("id"),
    )


def normalize_session_response_payload(
    payload: dict,
    *,
    session_id: str = "",
    active_session_id: str = "",
    preserve_existing: bool = True,
) -> dict:
    if not isinstance(payload, dict):
        return payload

    target_session_id = clean_session_id(session_id) or extract_session_id(payload)
    target_active_session_id = clean_session_id(active_session_id) or extract_active_session_id(payload) or target_session_id

    if not target_session_id and not target_active_session_id:
        return payload

    result = deepcopy(payload)

    existing_session_id = clean_session_id(result.get("session_id"))
    existing_active_id = clean_session_id(result.get("active_session_id"))

    if target_session_id and (not preserve_existing or not existing_session_id):
        result["session_id"] = target_session_id

    if target_active_session_id and (not preserve_existing or not existing_active_id):
        result["active_session_id"] = target_active_session_id

    debug = result.get("debug")
    if not isinstance(debug, dict):
        debug = {}

    if target_session_id and (not preserve_existing or not clean_session_id(debug.get("requested_session_id"))):
        debug["requested_session_id"] = target_session_id

    if target_session_id and (not preserve_existing or not clean_session_id(debug.get("session_id"))):
        debug["session_id"] = target_session_id

    if target_active_session_id and (not preserve_existing or not clean_session_id(debug.get("active_session_id"))):
        debug["active_session_id"] = target_active_session_id

    debug["session_response_finalizer"] = True
    result["debug"] = debug

    session = result.get("session")
    if isinstance(session, dict):
        if target_session_id and (not preserve_existing or not clean_session_id(session.get("id"))):
            session["id"] = target_session_id
        result["session"] = session

    assistant_message = result.get("assistant_message")
    if isinstance(assistant_message, dict):
        if target_session_id and (not preserve_existing or not clean_session_id(assistant_message.get("session_id"))):
            assistant_message["session_id"] = target_session_id
        result["assistant_message"] = assistant_message

    return result


def should_normalize_session_response(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False

    keys = {
        "session_id",
        "active_session_id",
        "requested_session_id",
        "session",
        "assistant_message",
        "debug",
    }

    if any(key in payload for key in keys):
        return bool(extract_session_id(payload) or extract_active_session_id(payload))

    return False


def finalize_session_response_payload(payload: dict) -> dict:
    if not should_normalize_session_response(payload):
        return payload

    return normalize_session_response_payload(payload)
''', encoding="utf-8")

SMOKE.write_text(r'''
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
''', encoding="utf-8")

print("installed Session Response Finalizer v1 service and smoke")
