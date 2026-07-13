"""
NOVA normal chat carryover guard service.

Extracted from:
NOVA_PHASE4G_NORMAL_CHAT_AUTONOMY_CARRYOVER_GUARD_20260701

Owns response repair logic.
Does not own Flask hooks.
"""

import json


def text(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def parse_response_json(response):
    try:
        data = json.loads(
            response.get_data(as_text=True)
        )

        return data if isinstance(data, dict) else None

    except Exception:
        return None


def write_response_json(response, data):
    try:
        payload = json.dumps(
            data,
            ensure_ascii=False,
        )

        response.set_data(payload)
        response.headers["Content-Length"] = str(
            len(response.get_data())
        )
        response.headers["Content-Type"] = "application/json"

    except Exception:
        pass

    return response


def assistant_text(data):
    if not isinstance(data, dict):
        return ""

    assistant = data.get("assistant_message")

    if isinstance(assistant, dict):
        return text(
            assistant.get("text")
            or assistant.get("content")
            or assistant.get("message")
        )

    return text(
        data.get("text")
        or data.get("content")
        or data.get("message")
    )


def repair_normal_chat_carryover(
    data,
    request_data,
):
    if not isinstance(data, dict):
        return data

    user_text = text(
        request_data.get("message")
        or request_data.get("text")
        or request_data.get("content")
    )

    normalized = user_text.lower().strip(" .!?")

    if normalized not in {
        "hi",
        "hello",
        "hey",
        "yo",
    }:
        return data

    current_assistant_text = assistant_text(data)

    if "nova autonomy task brief" not in current_assistant_text.lower():
        return data

    session_id = text(
        data.get("session_id")
        or data.get("active_session_id")
        or request_data.get("session_id")
    )

    fixed_text = "Hey Richard - normal chat is still active."

    assistant = data.get("assistant_message")

    if not isinstance(assistant, dict):
        assistant = {
            "role": "assistant",
        }

    assistant["text"] = fixed_text
    assistant["content"] = fixed_text
    assistant["role"] = "assistant"

    if session_id:
        assistant["session_id"] = session_id
        assistant["active_session_id"] = session_id

    meta = assistant.get("meta")

    if not isinstance(meta, dict):
        meta = {}

    meta["render_source"] = (
        "normal_chat_autonomy_carryover_guard"
    )
    meta["normal_chat_priority"] = True

    assistant["meta"] = meta

    data["assistant_message"] = assistant
    data["ok"] = True

    if session_id:
        data["session_id"] = session_id
        data["active_session_id"] = session_id

    debug = data.get("debug")

    if not isinstance(debug, dict):
        debug = {}

    debug["route"] = "chat"
    debug["route_taken"] = "chat"
    debug["normal_chat_priority"] = True
    debug["suppressed_autonomy_carryover"] = True

    data["debug"] = debug

    return data