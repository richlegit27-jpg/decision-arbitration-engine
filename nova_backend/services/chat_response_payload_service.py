def build_chat_response_payload(
    result,
    assistant_message,
    session_id,
    session_service,
):
    return {
        "ok": result.get("ok", True),
        "assistant_message": assistant_message,
        "session_attachments": (
            result.get("session_attachments")
            if isinstance(result, dict)
            else []
        ) or [],
        "attachment_debug": {
            "active_session_id": (
                result.get("active_session_id")
                if isinstance(result, dict)
                else session_id
            ),
            "session_attachments_count": len(
                (
                    result.get("session_attachments")
                    if isinstance(result, dict)
                    else []
                ) or []
            ),
        },
        "active_session_id": (
            result.get("active_session_id")
            or result.get("session_id")
            or session_id
        ),
        "session": (
            result.get("session")
            or session_service.get_session(session_id)
        ),
        "saved_artifact": result.get("saved_artifact"),
        "runtime": {},
        "debug": result.get("debug") or {},
    }