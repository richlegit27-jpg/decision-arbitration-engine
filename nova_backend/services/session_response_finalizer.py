
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
