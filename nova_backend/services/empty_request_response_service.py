def build_empty_request_response(session_id):
    return {
        "ok": True,
        "session_id": session_id,
        "active_session_id": session_id,
        "assistant_message": {
            "role": "assistant",
            "text": "",
        },
        "text": "",
        "empty_request": True,
        "no_session_created": True,
    }